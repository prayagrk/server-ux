# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Base Report Manager",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "summary": "Control report visibility per model based on Access Rights",
    "author": "CIT Services, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/server-ux",
    "license": "AGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_groups_views.xml",
    ],
    "installable": True,
}
