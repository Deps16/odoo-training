# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    x_po_number = fields.Char(string='PO Number', help='Purchase Order Number')
    x_po_amount = fields.Monetary(string='PO Amount', currency_field='currency_id', help='Purchase Order Amount')
    x_project_type = fields.Selection([
        ('A/1', 'A/1'),
        ('A/2', 'A/2'),
        ('A/3', 'A/3'),
        ('A/4', 'A/4'),
    ], string='Project Type', default='A/1')
    
    x_project_director_id = fields.Many2one('res.users', string='Project Director', tracking=True)
    x_subcontractor_id = fields.Many2one('res.partner', string='Subcontractor', domain="[('is_company', '=', True)]")
    
    x_budget_ids = fields.One2many('project.budget', 'project_id', string='Project Budgets')
    
    # Reference field to map Laravel database IDs
    x_laravel_id = fields.Char(string='Laravel UUID Ref', index=True, copy=False)
