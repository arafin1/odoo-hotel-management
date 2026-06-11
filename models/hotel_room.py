from odoo import fields, models


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room Details'

    name = fields.Char(string='Room Number/Name', required=True)
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
    room_type = fields.Selection([
        ('standard', 'Standard'),
        ('deluxe', 'Deluxe'),
        ('suite', 'Suite')
    ], string='Room Type', default='standard', required=True)
    price_per_night = fields.Monetary(
        string='Price Per Night',
        currency_field='currency_id',
        required=True,
    )
    is_available = fields.Boolean(string='Is Available', default=True)
