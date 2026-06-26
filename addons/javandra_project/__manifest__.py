# -*- coding: utf-8 -*-
{
    'name': 'Javandra Project Management Custom',
    'version': '17.0.1.0.0',
    'category': 'Project',
    'summary': 'Customization of Project Module for Javandra Task Management Migration',
    'description': """
        This module inherits and extends Odoo 17 Project module to match Javandra's schema:
        - Inherit Project (added Director, Subcontractor, PO Number, PO Amount, Project Type, and Laravel ID).
        - Inherit Task/Site (added Supervisor, Subcontractor In Charge, BAST Date, Service Date, Done Date).
        - Add Site Chronology (Progress Logs, Images, Event Date).
    """,
    'author': 'Antigravity',
    'website': 'https://www.javandra.com',
    'depends': ['project', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'views/project_site_chronology_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
