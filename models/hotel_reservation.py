from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


RESERVED_STATES = ('confirmed', 'checked_in')


class HotelReservation(models.Model):
    _name = 'hotel.reservation'
    _description = 'Hotel Reservation'
    _order = 'checkin_date desc, id desc'

    customer_id = fields.Many2one('res.partner', string='Guest/Customer', required=True)
    room_id = fields.Many2one('hotel.room', string='Assigned Room', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
    )
    checkin_date = fields.Date(string='Check-in Date', required=True, default=fields.Date.context_today)
    checkout_date = fields.Date(
        string='Check-out Date',
        required=True,
        default=lambda self: fields.Date.add(fields.Date.context_today(self), days=1),
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)
    price_per_night = fields.Monetary(
        string='Price/Night',
        related='room_id.price_per_night',
        currency_field='currency_id',
        readonly=True,
    )
    night_count = fields.Integer(
        string='Nights',
        compute='_compute_reservation_amounts',
        store=True,
    )
    amount_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_reservation_amounts',
        currency_field='currency_id',
        store=True,
    )
    discount_amount = fields.Monetary(
        string='Discount',
        currency_field='currency_id',
        default=0.0,
    )
    tax_rate = fields.Float(string='Tax (%)', default=0.0)
    tax_amount = fields.Monetary(
        string='Tax',
        compute='_compute_reservation_amounts',
        currency_field='currency_id',
        store=True,
    )
    amount_total = fields.Monetary(
        string='Amount Due',
        compute='_compute_reservation_amounts',
        currency_field='currency_id',
        store=True,
    )

    @api.depends(
        'checkin_date',
        'checkout_date',
        'room_id.price_per_night',
        'discount_amount',
        'tax_rate',
    )
    def _compute_reservation_amounts(self):
        for record in self:
            nights = 0
            if record.checkin_date and record.checkout_date:
                nights = max((record.checkout_date - record.checkin_date).days, 0)

            subtotal = nights * record.room_id.price_per_night
            taxable_amount = max(subtotal - record.discount_amount, 0.0)

            record.night_count = nights
            record.amount_subtotal = subtotal
            record.tax_amount = taxable_amount * record.tax_rate / 100.0
            record.amount_total = taxable_amount + record.tax_amount

    @api.constrains('discount_amount', 'tax_rate', 'checkin_date', 'checkout_date', 'room_id')
    def _check_invoice_amounts(self):
        for record in self:
            if record.discount_amount < 0:
                raise ValidationError(_('Discount cannot be negative.'))
            if record.tax_rate < 0:
                raise ValidationError(_('Tax rate cannot be negative.'))
            if record.discount_amount > record.amount_subtotal:
                raise ValidationError(_('Discount cannot be greater than the reservation subtotal.'))

    @api.constrains('checkin_date', 'checkout_date')
    def _check_dates(self):
        for record in self:
            if (
                record.checkin_date
                and record.checkout_date
                and record.checkout_date <= record.checkin_date
            ):
                raise ValidationError(_('The check-out date must be after the check-in date.'))

    @api.constrains('room_id', 'checkin_date', 'checkout_date', 'state')
    def _check_room_overlap(self):
        Reservation = self.env['hotel.reservation']
        for record in self:
            if (
                record.state not in RESERVED_STATES
                or not record.room_id
                or not record.checkin_date
                or not record.checkout_date
            ):
                continue

            overlap = Reservation.search([
                ('id', '!=', record.id),
                ('room_id', '=', record.room_id.id),
                ('state', 'in', RESERVED_STATES),
                ('checkin_date', '<', record.checkout_date),
                ('checkout_date', '>', record.checkin_date),
            ], limit=1)
            if overlap:
                raise ValidationError(_(
                    'Room "%(room)s" is already reserved for the selected dates.',
                    room=record.room_id.display_name,
                ))

    # Workflow actions
    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft reservations can be confirmed.'))
            record.write({'state': 'confirmed'})

    def action_checkin(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Only confirmed reservations can be checked in.'))
            if not record.room_id.is_available:
                raise UserError(_(
                    'Room "%(room)s" is currently flagged as occupied.',
                    room=record.room_id.display_name,
                ))

            record.write({'state': 'checked_in'})
            record.room_id.write({'is_available': False})

    def action_checkout(self):
        for record in self:
            if record.state != 'checked_in':
                raise UserError(_('Only checked-in reservations can be checked out.'))

            record.write({'state': 'checked_out'})
            record.room_id.write({'is_available': True})

    def action_cancel(self):
        for record in self:
            if record.state not in ('draft', 'confirmed'):
                raise UserError(_('Only draft or confirmed reservations can be cancelled.'))

            record.write({'state': 'cancelled'})
