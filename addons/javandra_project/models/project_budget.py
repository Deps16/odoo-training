# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectBudget(models.Model):
    _name = 'project.budget'
    _description = 'Project Budget'
    _order = 'date desc, id desc'

    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    
    type = fields.Char(string='Budget Type', required=True, help='e.g., Material, Operational, Salary, etc.')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    description = fields.Text(string='Description')
    
    # Currency helper
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Reference field to map Laravel database IDs
    x_laravel_id = fields.Char(string='Laravel UUID Ref', index=True, copy=False)
