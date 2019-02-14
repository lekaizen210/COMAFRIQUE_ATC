#-*- encoding:utf-8 -*-

import base64
import StringIO
import csv
from odoo import api, fields, models, exceptions, _
import io
import xlrd
import os
import zipfile


class wizardUploadFdmWithAxe(models.TransientModel):
    _name = "purchase.request.margin.upload.fdmwithaxe.wizard"
    _description = "Uploads d'un fichier Excel contenant des fiches de marge"

    data_file_excel_fdm_axe = fields.Binary(string='Fichier Excel à charger', required=True)


    @api.multi
    def uploadFileExcelFdm(self):
        pass






