{
    'name': 'Hotel Management System',
    'version': '1.0',
    'summary': 'Manage hotel rooms, descriptions, reservations, and payments',
    'category': 'Hospitality',
    'author': 'Arafindev',
    'depends': ['base', 'web'],  # Inherits Odoo's core engine (and the res.partner customer table)
    'data': [
        # We will add XML security and view files here later!
        'security/hotel_security.xml',      
        'security/ir.model.access.csv',
        'views/hotel_room_views.xml',
        'reports/hotel_reservation_report.xml',
        'views/hotel_reservation_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    
}
