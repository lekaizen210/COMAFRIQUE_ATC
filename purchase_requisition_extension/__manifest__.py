# -*- coding: utf-8 -*-
{
    'name': "Expression de besoin",

    'summary': """
        Expression de besoin d'achat""",

    'description': """
        Ce module permet de centraliser les expressions de besoin au sein d'un processus de validation    """,

    'author': "VEONE",
    'website': "http://www.veone.net",


    'category': 'Purchase',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','purchase','crm','account','account_accountant', 'hr', 'stock', 'product'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/rules.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu_managment_view.xml',
        'views/purchaseRequestView.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}