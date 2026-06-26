# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    x_supervisor_id = fields.Many2one('res.users', string='Supervisor', tracking=True)
    x_subcontractor_id = fields.Many2one('res.partner', string='Subcontractor In Charge')
    
    x_done_date = fields.Date(string='Done Date')
    x_service_date = fields.Date(string='Service Date')
    x_bast_date = fields.Date(string='BAST Date', help='Berita Acara Serah Terima (Handover) Date')
    
    # Chronology relation
    x_chronology_ids = fields.One2many('project.site.chronology', 'project_site_id', string='Site Chronologies')
    
    # Reference field to map Laravel database IDs
    x_laravel_id = fields.Char(string='Laravel UUID Ref', index=True, copy=False)
