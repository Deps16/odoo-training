from odoo import fields,models



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    berak_count = fields.Integer(string='Hitung Berak')
    