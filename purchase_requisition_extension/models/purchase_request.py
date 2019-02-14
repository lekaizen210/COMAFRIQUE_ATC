# -*- coding:utf-8 -*-


import time
import werkzeug
from datetime import datetime
from odoo import api, fields, models, exceptions, _

class PurchseRequestType(models.Model):
    _name= "purchase.request.type"
    _description = "Purchase request managment"


    name=fields.Char('Nom', required=True)
    description= fields.Text('Description', required=False)
    type= fields.Selection([('revente', 'Achat pour revente'),('mission', 'type Missions liées à la vente'),
                ('formation', 'Formation'),('frais', 'Frais Généraux'),('investissement', 'Investissements')],
                           string="Type", required=True, default=False)
    amount_max= fields.Integer('Montant min à valider par la DG', required=True)


class PurchaseRequisition(models.Model):
    _name = 'purchase.request'
    _description = 'Expression de besoin'
    _inherit = 'mail.thread'
    _order = "name desc"

    @api.multi
    def unlink(self):
        for request in self:
            if request.state != 'draft':
                raise exceptions.ValidationError(
                    str("Vous ne pouvez pas supprimer ce ducument, veuillez le mettre d'abord en brouillon"))
        return super(PurchaseRequisition, self).unlink()

    @api.one
    @api.depends('margin_id')
    def _get_order_ref(self):
        self.margin_cost = self.margin_id.amount_total
        self.margin_rate = self.margin_id.margin_percent
        self.partner_id = self.margin_id.partner_id.id

    @api.one
    @api.depends('order_ref')
    def _get_order_id(self):
        order_id = self.env['purchase.order'].search([['name', '=', self.order_ref]])

    @api.one
    def _field_count(self):
        Purchase = self.env['purchase.order']
        purchase = Purchase.search_count([['request_id', '=', self.id]])
        self.nb_purchase = purchase

        Picking = self.env['stock.picking']
        picking = Picking.search_count([['request_id', '=', self.id]])
        self.nb_picking = picking

    @api.one
    @api.depends('line_ids')
    def _get_totals(self):
        self.amount_untaxed = sum(line.subtotal for line in self.line_ids)

        for line in self.line_ids:
            self.amount_tax += sum((sline.amount * line.price_unit * line.quantity) / 100 for sline in line.tax_id)

        self.amount_total = self.amount_tax + self.amount_untaxed

    @api.model
    def _get_default_employee(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        print(employee.name)
        if employee :
            return employee.id
        return False

    @api.model
    def _get_number_expression(self):
        name = self.env['ir.sequence'].next_by_code('purchase.request') or _('/')
        return name

    name = fields.Char('Référence', size=128, required=True, default=_get_number_expression, readonly=True, copy=False)
    order_ref = fields.Char('Référence BC', size=128, help='Référence de la commande client')
    type_id= fields.Many2one('purchase.request.type', 'Type', required=True)
    type = fields.Selection([('revente', 'Achat pour revente'), ('mission', 'type Missions liées à la vente'),
                             ('formation', 'Formation'), ('frais', 'Frais Généraux'),
                             ('investissement', 'Investissements')],
                            string="Type", related='type_id.type', default=False)
    initiateur_id= fields.Many2one('res.users', 'Initiateur', required=True, default= lambda self: self.env.uid)
    line_ids= fields.One2many('purchase.request.line', 'request_id', 'Lignes', required=True)
    date = fields.Date('Date de demande', help='Date', required=True)
    deadline = fields.Date("Echéance souhaitée", required=True)
    #url_link = fields.Char("Lien", compute=_get_url_direct_link)
    employee_id = fields.Many2one('hr.employee', 'Demandeur', required=True, readonly=True, default=_get_default_employee,
                                  help='Employé en charge de la demande selectionné automatiquement')
    order_id = fields.Many2one('purchase.order', 'Commande Frs', compute=_get_order_id, store=True)
    #order_ref = fields.Char('Référence commande', copy=False)
    budget_id = fields.Many2one('crossovered.budget', 'Budget', copy=False)
    margin_id = fields.Many2one('purchase.request.margin', 'Réf. fiche de marge', copy=False)
    #margin_cost = fields.Float('Coût global', store=True, compute=_get_order_ref)
    #margin_rate = fields.Float('Taux de marge', store=True, compute=_get_order_ref)
    #partner_id = fields.Many2one('res.partner', 'Client', required=False, compute=_get_order_ref, store=True)
    job_id = fields.Many2one('hr.job', 'Poste', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', 'Département', related='employee_id.department_id')
    amount_tax = fields.Float('Taxes', compute=_get_totals)
    amount_untaxed = fields.Float('Total hors-taxe', compute=_get_totals)
    amount_total = fields.Float('Montant Total', compute=_get_totals)
    justification = fields.Text('Justification', required=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('dsc', 'DSC'),
        ('rh', 'RH'),
        ('controle', 'Contrôle de gestion'),
        ('operation', 'Opération'),
        ('direction', 'Direction Générale'),
        ('administration', 'Service Q & L'),
        ('refus', 'Refusé'),
        ('standby', 'Reporté'),
        ('done', 'Terminé'),
    ], 'Etat', select=True, default='draft', track_visibility='onchange')

    @api.one
    def action_draft(self):
        self.state = 'draft'

    @api.one
    def action_refus(self):
        self.state = 'refus'

    @api.one
    @api.depends('type_id')
    def action_submit(self):
        if self.type_id.type != 'formation':
            self.state = 'dsc'
        else :
            self.state = 'controle'

    @api.one
    @api.depends('type_id')
    def action_dsc(self):
        if self.type_id.type == 'mission':
            self.state = 'rh'
        elif self.type_id.type == 'revente':
            self.state = 'operation'
        else :
            self.state = 'contorle'


    @api.one
    @api.depends('type_id')
    def action_rh(self):
        if self.type_id.type == 'mission':
            self.state = 'operation'


    @api.one
    @api.depends('type_id')
    def action_operation(self):
        if self.type_id.amount_max <= self.amount_total :
            self.state = 'direction'
        else:
            self.state = 'done'

    @api.one
    @api.depends('type_id')
    def action_direction(self):
        self.state = 'done'



class PurchaseRequisitionLine(models.Model):
    _name = 'purchase.request.line'
    _description = 'Ligne de besoin'

    @api.one
    @api.depends('price_unit', 'quantity')
    def _get_subtotal(self):
        self.subtotal = self.price_unit * self.quantity

    @api.one
    @api.depends('prof')
    def _get_proforma(self):
        prof = 'Non'
        if self.prof:
            self.proforma = 'Oui'

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.description or self.product_id.name
        """self.available_qty = self.product_id.qty_available
        self.price_unit = self.product_id.standard_price"""

    def _get_product_domain(self):
        return self.request_id.request_type.id

    @api.onchange('analytic_account_id')
    def onchange_analytic_account_id(self):
        self.sous_section_id = self.analytic_account_id.section_child_id.id

    product_id = fields.Many2one('product.product', 'Article')
    name = fields.Char('Description', required=True)
    partner_id = fields.Many2one('res.partner', 'Fournisseur', domain=[('supplier', '=', True)])
    section_id = fields.Many2one('account.analytic.account', 'Axe',
                                 domain=[('type', '=', 'section'), ('section_id', '=', False)])
    sous_section_id = fields.Many2one('account.analytic.account', 'Sous-Axe')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytique')
    quantity = fields.Float('Quantité', default=1)
    available_qty = fields.Float('Qté dispo')
    price_unit = fields.Float('Prix unitaire')
    tax_id = fields.Many2many('account.tax', domain=[('type_tax_use', '=', 'purchase')])
    subtotal = fields.Float('Sous-total HT', compute=_get_subtotal, store=True)
    prof = fields.Boolean('Prof.')
    proforma = fields.Char(compute=_get_proforma)
    request_id = fields.Many2one('purchase.request', 'Besoin')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('dsc', 'DSC'),
        ('rh', 'RH'),
        ('controle', 'Contrôle de gestion'),
        ('direction', 'Direction Générale'),
        ('administration', 'Service Q & L'),
        ('refus', 'Refusé'),
        ('standby', 'Reporté'),
        ('done', 'Terminé'),
    ], 'Etat', select=True, default='draft', track_visibility='onchange', related='request_id.state')




class request_validate_budget(models.Model):
    _name = 'purchase.request.budget'
    _description = 'Lignes de budget valides'
    _rec_name = 'request_id'

    @api.multi
    @api.depends('analytic_account_id', 'budget_id')
    def _get_analytic_section(self):
        self.section_id = self.analytic_account_id.section_id.id
        self.section_child_id = self.analytic_account_id.section_child_id.id
        self.department_id = self.analytic_account_id.department_id.id

    @api.one
    def _get_process(self):
        self.process = self.request_id.process

    section_id = fields.Many2one('account.analytic.account', 'Axe analytique', compute=_get_analytic_section,
                                 store=True)
    section_child_id = fields.Many2one('account.analytic.account', 'Sous-axe analytique', compute=_get_analytic_section,
                                       store=True)
    department_id = fields.Many2one('hr.department', 'Departement', compute=_get_analytic_section, store=True)
    create_date = fields.Datetime('Date de création')
    create_uid = fields.Many2one('res.users', 'Validé par')
    request_id = fields.Many2one('purchase.request', 'Demande', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Compte analytique')
    budget_id = fields.Many2one('crossovered.budget', 'Budget', required=True)
    amount = fields.Float('Montant validé')
    planned_amount = fields.Float('Montant prévu')
    invoice_id = fields.Many2one('account.invoice', 'Facture')
    state = fields.Selection([
        ('nconsomme', 'En attente de consommation'),
        ('consomme', 'Consommé'),
    ], 'Etat de consommation', select=True, readonly=True, default='nconsomme', track_visibility='onchange')
    process = fields.Selection([('depense', 'Frais généraux & Marketing'),
                                ('investissement', 'Autorisation d\'investissement'),
                                ('revente', 'Achat pour revente'),
                                ('formation', 'Formation du personnel'),
                                ('appro', 'Approvisionnement de stock'),
                                ('tiers', 'Achat pour compte de tiers'),
                                ], 'Type de la demande', select=True, readonly=False, compute=_get_process)


class request_budget_line(models.Model):
    _name = 'purchase.request.budget.line'
    _rec_name = 'analytic_account_id'

    section_id = fields.Many2one('account.analytic.account', 'Axe')
    sous_section_id = fields.Many2one('account.analytic.account', 'Sous-Axe')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Compte analytique')
    budget_id = fields.Many2one('crossovered.budget', 'Budget', required=False)
    request_id = fields.Many2one('purchase.request', 'Demande', required=False)
    request_budget_id = fields.Many2one('purchase.request.budget', 'Engagement', required=False)
    montant_prevu = fields.Float('Montant prévu')
    montant_consomme = fields.Float('Montant consommé')
    montant_engage = fields.Float('Montant engagé')
    montant_encours = fields.Float('En cours val. Direction')
    demande_encours = fields.Float('Demande en cours')
    montant_restant = fields.Float('Montant restant')
    color = fields.Integer('Couleur')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('department', 'Département'),
        ('controle', 'Contrôle de gestion'),
        ('direction', 'Direction Générale'),
        ('administration', 'Admin. des ventes'),
        ('refus', 'Refusé'),
        ('standby', 'Reporté'),
        ('done', 'Terminé'),
    ], 'Etat', select=True, default='draft', track_visibility='onchange', related='request_id.state', store=True)