# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectSiteChronology(models.Model):
    _name = 'project.site.chronology'
    _description = 'Project Site Chronology'
    _order = 'event_date desc, id desc'

    project_site_id = fields.Many2one('project.task', string='Project Site/Task', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user)
    
    title = fields.Char(string='Title', required=True)
    event_date = fields.Date(string='Event Date', default=fields.Date.context_today)
    description = fields.Html(string='Description')
    
    # Image fields
    image = fields.Binary(string='Attachment Image')
    image_name = fields.Char(string='Image Name')
    
    # Reference field to map Laravel database IDs
    x_laravel_id = fields.Char(string='Laravel UUID Ref', index=True, copy=False)
