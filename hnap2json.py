#!/usr/bin/python
# -*- coding: utf-8 -*-

json_output    = {}
error_output   = []
debug_output   = {}

input_files    = ['data/TBS_V2/aplCANreg_metadata_HNAP_exemple_minimum.xml','data/TBS_V2/aplCANreg_metadata_HNAP_exemple.xml']
input_file     = 'data/full_populated.xml'

source_hnap    = '...GeoNetworkServer.../csw?service=CSW&version=2.0.2&request=GetRecordById&outputSchema=csw:IsoRecord&id='

import argparse
parser         = argparse.ArgumentParser()
#parser.add_argument("-jf")
#parser.add_argument("-jo")
#parser.add_argument("-af")
#parser.add_argument("-ao")
#parser.add_argument("-ef")
#parser.add_argument("-eo")
args           = parser.parse_args()

import time
iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

import sys
from lxml import etree

import collections
import re

#import codecs
#import json
#import os
#import csv

def fetchXMLArray(objectToXpath,xpath):
	return objectToXpath.xpath(xpath, namespaces={'gmd':'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco','gml':'http://www.opengis.net/gml/3.2'})

def fetchXMLValues(objectToXpath,xpath):
	values = []
	r = fetchXMLArray(objectToXpath,xpath)
	if(len(r)):
		for namePart in r:
			if namePart.text == None:
				values.append('')
			else:
				values.append(namePart.text.strip())
	return values

def reportError(errorText):
	global error_output
	global OGDMES2ID
	error_output.append(errorText)
def sanitySingle(pre,values):
	values = list(set(values))
	if len(values) > 1:
		reportError(pre+',multiple of a single value,"'+','.join(values)+'"')
		return False
	return True
def sanityFirst(values):
	if len(values) < 1:
		return ''
	else:
		return values[0]

def main():
	# Read the file, should be a streamed input in the future
	root           = etree.parse(input_file)
	# Parse the root and itterate over each record
	records = fetchXMLArray(root,"/gmd:MD_Metadata")
	for record in records:

		json_record = {}

		##### HNAP CORE LANGUAGE
		##################################################
		OGDMES_property = 'HNAP_Language'
		tmp = fetchXMLValues(record,"gmd:language/gco:CharacterString")
		if False == sanitySingle(OGDMES_property,tmp):
			# Language is required, the rest can't be processed
			# for errors if the primary language is not certain
			HNAP_primary_language = False
		else:
			HNAP_primary_language = sanityFirst(tmp).split(';')[0].strip()
			if HNAP_primary_language == 'eng':
				CKAN_primary_lang   = 'en'
				CKAN_secondary_lang = 'fr'
				OGDMES_primary_lang = 'English'
				OGDMES_secondary_lang = 'French'
			else:
				CKAN_primary_lang   = 'fr'
				CKAN_secondary_lang = 'en'
				OGDMES_primary_lang = 'French'
				OGDMES_secondary_lang = 'English'
			debug_output['00-HNAP RECORD PRIMARY LANGUAGE'] = HNAP_primary_language

		##### OGDMES-01 fileIdentifier
		##################################################
		OGDMES_property = 'fileIdentifier'
		tmp = fetchXMLValues(record,"gmd:fileIdentifier/gco:CharacterString")
		if False == sanitySingle(OGDMES_property,tmp):
			# Language is required, the rest can't be processed
			# for errors if the primary language is not certain
			OGDMES_fileIdentifier = False
		else:
			OGDMES_fileIdentifier = sanityFirst(tmp)
			json_record['id'] = OGDMES_fileIdentifier
			debug_output['01-OGDMES fileIdentifier'] = OGDMES_fileIdentifier

		##### Fail out if you don't have either a primary language or ID
		##################################################
		if HNAP_primary_language == False or OGDMES_fileIdentifier == False:
			break

		debug_output['01-OGDMES fileIdentifier'] = OGDMES_fileIdentifier

		# From here on on continue if you can to collect errors to send to
		# FGP Help desk.  If you fail on each error each need to get fixed
		# in series but if you collect everything you can they can address
		# them a series at a time speeding up the process of getting their
		# records into the system.
		
		##### OGDMES-02 shortKey
		##################################################
		OGDMES_property = 'shortKey'
		# Shortkey is not defined in HNAP, it will eventually be required
		# as collisions will happen when there are significantly more
		# records.  When that happens shortkeys will need to be provided
		# and the XPATH will need to be offered and used first.  The logic
		# will be 1) if offered use the provided shortkey 2) if not offered
		# use this math derived shortkey.
		json_record[OGDMES_property] = OGDMES_fileIdentifier[0:8]
		debug_output['02-OGDMES shortKey [calculated]'] = OGDMES_fileIdentifier[0:8]

		##### OGDMES-03 metadataRecordLanguage
		##################################################
		# This is presently the same as the the cor HNAP language but this
		# OGDMES property may dissapear, it was included prior to the
		# knowledge that the HNAP record was bilingual
		OGDMES_property = 'metadataRecordLanguage'
		json_record[OGDMES_property] = HNAP_primary_language
		debug_output['03-OGDMES metadataRecordLanguage'] = HNAP_primary_language

		##### OGDMES-04 characterSet
		##################################################
		OGDMES_property = 'characterSet'
		tmp = fetchXMLValues(record,"gmd:characterSet/gmd:MD_CharacterSetCode")
		sanitySingle(OGDMES_property,tmp)
		json_record[OGDMES_property] = sanityFirst(tmp)
		debug_output['04-OGDMES characterSet'] = sanityFirst(tmp)

		##### OGDMES-05 parentIdentifier
		##################################################
		OGDMES_property = 'parentIdentifier'
		tmp = fetchXMLValues(record,"gmd:parentIdentifier/gco:CharacterString")
		sanitySingle(OGDMES_property,tmp)
		json_record['parent_id'] = sanityFirst(tmp)
		debug_output['05-OGDMES parentIdentifier'] = sanityFirst(tmp)

		##### OGDMES-06 hierarchyLevel
		##################################################
		OGDMES_property = 'hierarchyLevel'
		tmp = fetchXMLValues(record,"gmd:hierarchyLevel/gmd:MD_ScopeCode")
		sanitySingle(OGDMES_property,tmp)
		json_record[OGDMES_property] = {}
		if tmp == None or len(tmp) < 1:
			reportError(OGDMES_property+",no value,")
			json_record[OGDMES_property][CKAN_primary_lang] = ''
			json_record[OGDMES_property][CKAN_secondary_lang] = ''
		else:
			(primary,secondary) = sanityFirst(tmp).strip().split(';')
			json_record[OGDMES_property][CKAN_primary_lang] = primary.strip()
			json_record[OGDMES_property][CKAN_secondary_lang] = secondary.strip()

		debug_output['06-OGDMES hierarchyLevel-'+CKAN_primary_lang] = json_record[OGDMES_property][CKAN_primary_lang]
		debug_output['06-OGDMES hierarchyLevel-'+CKAN_secondary_lang] = json_record[OGDMES_property][CKAN_secondary_lang]

		##### OGDMES-07 metadataContact
		##################################################
		OGDMES_property = 'metadataContact'
		primary_vals = []
		second_vals = []

		# organizationName
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang,tmp)
		primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:organisationName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang,tmp)
		second_vals.append(sanityFirst(tmp))

		# voice
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang,tmp)
		primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang,tmp)
		second_vals.append(sanityFirst(tmp))

		# electronicMailAddress
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang,tmp)
		primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang,tmp)
		second_vals.append(sanityFirst(tmp))

		json_record[OGDMES_property] = {}
		json_record[OGDMES_property][CKAN_primary_lang] = ','.join(primary_vals)
		json_record[OGDMES_property][CKAN_secondary_lang] = ','.join(second_vals)

		debug_output['07-OGDMES metadataContact'] = json_record[OGDMES_property]['en']
		debug_output['07-OGDMES metadataContact'] = json_record[OGDMES_property]['fr']

		##### OGDMES-08 metadataRecordDateStamp
		##################################################
		OGDMES_property = 'metadataRecordDateStamp'
		tmp = fetchXMLValues(record,"gmd:dateStamp/gco:Date")
		sanitySingle(OGDMES_property,tmp)
		json_record['characterSet'] = sanityFirst(tmp)
		debug_output['08-OGDMES metadataRecordDateStamp'] = sanityFirst(tmp)

		##### OGDMES-09 metadataStandardName
		##################################################
		json_record['metadataStandardName'] = {}
		json_record['metadataStandardName']['en'] = 'Government of Canada’s Open Geospatial Data Metadata Element Set'
		json_record['metadataStandardName']['fr'] = 'Données ouvertes géospatiales du gouvernement du Canada – Ensemble d’éléments de métadonnées'
		debug_output['09-OGDMES metadataStandardName'] = json_record['metadataStandardName']['en']
		debug_output['09-OGDMES metadataStandardName'] = json_record['metadataStandardName']['fr']

		##### OGDMES-10 metadataURI
		##################################################
		json_record['url'] = source_hnap+OGDMES_fileIdentifier
		debug_output['10-OGDMES metadataURI'] = json_record['url']

		##### OGDMES-11 locale
		##################################################
		OGDMES_property = 'locale'
		tmp = fetchXMLValues(record,"gmd:MD_Metadata/gmd:locale/gmd:PT_Locale/gmd:languageCode/gmd:LanguageCode")
		sanitySingle(OGDMES_property,tmp)
		json_record[OGDMES_property] = {}
		if tmp == None or len(tmp) < 1:
			reportError(OGDMES_property+",no value,")
			json_record[OGDMES_property][CKAN_primary_lang] = ''
			json_record[OGDMES_property][CKAN_secondary_lang] = ''
		else:
			(primary,secondary) = sanityFirst(tmp).strip().split(';')
			json_record[OGDMES_property][CKAN_primary_lang] = primary.strip()
			json_record[OGDMES_property][CKAN_secondary_lang] = secondary.strip()

		debug_output['11-OGDMES locale'+OGDMES_primary_lang] = json_record[OGDMES_property][CKAN_primary_lang]
		debug_output['11-OGDMES locale'+OGDMES_secondary_lang] = json_record[OGDMES_property][CKAN_secondary_lang]

		##### OGDMES-12 title
		##################################################
		OGDMES_property = 'title'
		json_record[OGDMES_property] = {}

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang,tmp)
		json_record[OGDMES_property][CKAN_primary_lang] = sanityFirst(tmp)
		
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang,tmp)
		json_record[OGDMES_property][CKAN_secondary_lang] = sanityFirst(tmp)

		debug_output['12-OGDMES title'+OGDMES_primary_lang] = json_record[OGDMES_property][CKAN_primary_lang]
		debug_output['12-OGDMES title'+OGDMES_secondary_lang] = json_record[OGDMES_property][CKAN_secondary_lang]

		##### OGDMES-13 dateContributed
		##################################################
		OGDMES_property = 'dateContributed'
		json_record[OGDMES_property] = {}
		debug_output['13-OGDMES dateContributed'] = '[CKAN SUPPLIED]'

		##### OGDMES-14 datePublished
		##### OGDMES-15 dateModified
		##################################################
		# This one is a little different, we have to do this bad boy manually
		r = record.xpath("gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date", namespaces={'gmd':'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco'})
		if(len(r)):
			for cn in r:
				if cn[1][0].text == u'publication; publication':
					json_record['date_published'] = cn[0][0].text.strip()
					debug_output['14-OGDMES date_published'] = json_record['date_published']
				if cn[0][0].text == u'publication; publication':
					json_record['date_published'] = cn[1][0].text.strip()
					debug_output['14-OGDMES date_published'] = json_record['date_published']
				if cn[1][0].text == u'revision; révision':
					json_record['date_modified'] = cn[0][0].text.strip()
					debug_output['15-OGDMES date_modified'] = json_record['date_modified']
				if cn[0][0].text == u'revision; révision':
					json_record['date_modified'] = cn[1][0].text.strip()
					debug_output['15-OGDMES date_modified'] = json_record['date_modified']

		##### OGDMES-16 identifier
		##################################################
		OGDMES_property = 'identifier'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString")
		sanitySingle(OGDMES_property,tmp)
		json_record['digital_object_identifier'] = sanityFirst(tmp)
		debug_output['16-OGDMES identifier'] = sanityFirst(tmp)

		##### OGDMES-17 individualName
		##################################################
		OGDMES_property = 'individualName'
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:individualName/gco:CharacterString")
		sanitySingle(OGDMES_property,tmp)
		json_record['individual_name'] = sanityFirst(tmp)
		debug_output['17-OGDMES individualName'] = sanityFirst(tmp)

		##### OGDMES-18 organisationName
		##################################################
		OGDMES_property = 'organisationName'
		json_record['responsible_organization'] = {}
		primary_vals = []
		second_vals = []
		# A bit unique, some manual work to strip the GC object

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString")
		if tmp != None and len(tmp) > 0:
			values = tmp[0].strip().split(';')
			if values[0] != 'Government of Canada' and values[0] != 'Gouvernement du Canada':
				reportError(organisationName+',"Bad organizationName, no Government of Canada",""')
			del values[0]
			for GOC_Div in values:
				if GOC_Div.strip() in GC_Registry_of_Applied_Terms:
					primary_vals.append(GOC_Div.strip())

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty/gmd:organisationName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if tmp != None and len(tmp) > 0:
			values = tmp[0].strip().split(';')
			if values[0] != 'Government of Canada' and values[0] != 'Gouvernement du Canada':
				reportError(organisationName+',"Bad organizationName, no Government of Canada",""')
			del values[0]
			for GOC_Div in values:
				if GOC_Div.strip() in GC_Registry_of_Applied_Terms:
					primary_vals.append(GOC_Div.strip())

		json_record['responsible_organization'][CKAN_primary_lang] = ','.join(primary_vals)
		json_record['responsible_organization'][CKAN_secondary_lang] = ','.join(second_vals)

		debug_output['18-OGDMES organisationName'+OGDMES_primary_lang] = json_record['responsible_organization'][CKAN_primary_lang]
		debug_output['18-OGDMES organisationName'+OGDMES_secondary_lang] = json_record['responsible_organization'][CKAN_secondary_lang]

		##### OGDMES-19 positionName
		##################################################
		OGDMES_property = 'positionName'
		json_record['position_name'] = {}
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:positionName/gco:CharacterString")
		sanitySingle(OGDMES_property,tmp)
		json_record['position_name'][CKAN_primary_lang] = sanityFirst(tmp)
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:positionName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property,tmp)
		json_record['position_name'][CKAN_secondary_lang] = sanityFirst(tmp)
		
		debug_output['19-OGDMES positionName'+OGDMES_primary_lang] = json_record['position_name'][CKAN_primary_lang]
		debug_output['19-OGDMES positionName'+OGDMES_secondary_lang] = json_record['position_name'][CKAN_secondary_lang]


#	'contactInfoEnglish'            :'20e',
#	'contactInfoFrench'             :'20f',
		##### OGDMES-20 contactInfo
		##################################################
		OGDMES_property = 'contactInfo'

		primary_vals = []
		second_vals	= []

		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:deliveryPoint/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang+'deliveryPoint',tmp)
		primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:city/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang+'city',tmp)
		primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:administrativeArea/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang+'administrativeArea',tmp)
		primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:postalCode/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang+'postalCode',tmp)
		primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:country/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang+'country',tmp)
		primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang+'electronicMailAddress',tmp)
		primary_vals.append(sanityFirst(tmp))

		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:deliveryPoint/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang+'deliveryPoint',tmp)
		second_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:city/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang+'city',tmp)
		second_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:administrativeArea/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang+'administrativeArea',tmp)
		second_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:postalCode/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang+'postalCode',tmp)
		second_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:country/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang+'country',tmp)
		second_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang+'electronicMailAddress',tmp)
		second_vals.append(sanityFirst(tmp))

		json_record['contactInfo'] = {}
		json_record['contactInfo'][CKAN_primary_lang] = ','.join(primary_vals)
		json_record['contactInfo'][CKAN_secondary_lang] = ','.join(second_vals)

		debug_output['20-OGDMES contactInfo'+OGDMES_primary_lang] = json_record['position_name'][CKAN_primary_lang]
		debug_output['20-OGDMES contactInfo'+OGDMES_secondary_lang] = json_record['position_name'][CKAN_secondary_lang]

		##### OGDMES-21 role
		##################################################
		OGDMES_property = 'role'
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode")
		sanitySingle(OGDMES_property,tmp)
		json_record['responsible_role'] = {}
		if tmp == None or len(tmp) < 1:
			reportError(OGDMES_property+",no value,")
			json_record['responsible_role'][CKAN_primary_lang] = ''
			json_record['responsible_role'][CKAN_secondary_lang] = ''
		else:
			(primary,secondary) = sanityFirst(tmp).strip().split(';')
			json_record['responsible_role'][CKAN_primary_lang] = primary.strip()
			json_record['responsible_role'][CKAN_secondary_lang] = secondary.strip()

		debug_output['21-OGDMES role'] = json_record['responsible_role'][CKAN_primary_lang]
		debug_output['21-OGDMES role'] = json_record['responsible_role'][CKAN_secondary_lang]

		##### OGDMES-22 abstract
		##################################################
		OGDMES_property = 'abstract'
		json_record['notes'] = {}

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString")
		sanitySingle(OGDMES_property+CKAN_primary_lang,tmp)
		json_record['notes'][CKAN_primary_lang] = sanityFirst(tmp)
		
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property+CKAN_secondary_lang,tmp)
		json_record['notes'][CKAN_secondary_lang] = sanityFirst(tmp)

		debug_output['22-OGDMES abstract'+OGDMES_primary_lang] = json_record['notes'][CKAN_primary_lang]
		debug_output['22-OGDMES abstract'+OGDMES_secondary_lang] = json_record['notes'][CKAN_secondary_lang]

		##### OGDMES-23 descriptiveKeywords
		##################################################
		OGDMES_property = 'descriptiveKeywords'
		json_record['keywords'] = {}

		primary_vals = []
		second_vals	= []

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString")
		for value in tmp:
			p = re.compile('^[A-Z][A-Z] [^>]+ > ')
			value = p.sub( '', value)
			primary_vals.append(value)
		
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		for value in tmp:
			p = re.compile('^[A-Z][A-Z] [^>]+ > ')
			value = p.sub( '', value)
			second_vals.append(value)

		json_record['keywords'][CKAN_primary_lang] = ','.join(primary_vals)
		json_record['keywords'][CKAN_secondary_lang] = ','.join(second_vals)

		debug_output['23-OGDMES descriptiveKeywords'+OGDMES_primary_lang] = json_record['keywords'][CKAN_primary_lang]
		debug_output['23-OGDMES descriptiveKeywords'+OGDMES_secondary_lang] = json_record['keywords'][CKAN_secondary_lang]

		##### OGDMES-24 status
		##################################################
		OGDMES_property = 'status'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode")
		sanitySingle(OGDMES_property,tmp)
		json_record[OGDMES_property] = {}
		if tmp == None or len(tmp) < 1:
			reportError(OGDMES_property+",no value,")
			json_record[OGDMES_property][CKAN_primary_lang] = ''
			json_record[OGDMES_property][CKAN_secondary_lang] = ''
		else:
			(primary,secondary) = sanityFirst(tmp).strip().split(';')
			json_record[OGDMES_property][CKAN_primary_lang] = primary.strip()
			json_record[OGDMES_property][CKAN_secondary_lang] = secondary.strip()

		debug_output['24-OGDMES status'+OGDMES_primary_lang] = json_record[OGDMES_property][CKAN_primary_lang]
		debug_output['24-OGDMES status'+OGDMES_secondary_lang] = json_record[OGDMES_property][CKAN_secondary_lang]

		##### OGDMES-25 associationType
		##################################################
		OGDMES_property = 'associationType'
		tmp = fetchXMLValues(record,"gmd:aggregationInfo/gmd:MD_AggregateInformation/gmd:associationType/gmd:DS_AssociationTypeCode")
		sanitySingle(OGDMES_property,tmp)
		json_record['association_type'] = sanityFirst(tmp)
		debug_output['25-OGDMES associationType'] = sanityFirst(tmp)

		##### OGDMES-26 aggregateDataSetIdentifier
		##################################################
		OGDMES_property = 'aggregateDataSetIdentifier'
		tmp = fetchXMLValues(record,"gmd:aggregationInfo/gmd:MD_AggregateInformation/gmd:aggregateDataSetIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString")
		sanitySingle(OGDMES_property,tmp)
		json_record['aggregate_identifier'] = sanityFirst(tmp)
		debug_output['26-OGDMES aggregateDataSetIdentifier'] = sanityFirst(tmp)

		##### OGDMES-27 spatialRepresentationType
		##################################################
		OGDMES_property = 'spatialRepresentationType'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode")
		sanitySingle(OGDMES_property,tmp)
		json_record['spatial_representation_type'] = {}
		if tmp == None or len(tmp) < 1:
			reportError(OGDMES_property+",no value,")
			json_record['spatial_representation_type'][CKAN_primary_lang] = ''
			json_record['spatial_representation_type'][CKAN_secondary_lang] = ''
		else:
			(primary,secondary) = sanityFirst(tmp).strip().split(';')
			json_record['spatial_representation_type'][CKAN_primary_lang] = primary.strip()
			json_record['spatial_representation_type'][CKAN_secondary_lang] = secondary.strip()

		debug_output['27-OGDMES spatialRepresentationType'+OGDMES_primary_lang] = json_record['spatial_representation_type'][CKAN_primary_lang]
		debug_output['27-OGDMES spatialRepresentationType'+OGDMES_secondary_lang] = json_record['spatial_representation_type'][CKAN_secondary_lang]

		##### OGDMES-28 topicCategory
		##################################################
		OGDMES_property = 'topicCategory'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode")
		sanitySingle(OGDMES_property,tmp)
		json_record['topic_category'] = sanityFirst(tmp)
		debug_output['28-OGDMES topicCategory'] = sanityFirst(tmp)

		##### OGDMES-29 westBoundingLongitude
		##################################################
		OGDMES_property = 'westBoundingLongitude'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal")
		sanitySingle(OGDMES_property,tmp)
		json_record[OGDMES_property] = sanityFirst(tmp)
		debug_output['29-OGDMES westBoundingLongitude'] = sanityFirst(tmp)

		##### OGDMES-30 eastBoundingLongitude
		##################################################
		OGDMES_property = 'eastBoundingLongitude'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal")
		sanitySingle(OGDMES_property,tmp)
		json_record[OGDMES_property] = sanityFirst(tmp)
		debug_output['30-OGDMES eastBoundingLongitude'] = sanityFirst(tmp)

		##### OGDMES-31 southBoundingLongitude
		##################################################
		OGDMES_property = 'southBoundingLongitude'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal")
		sanitySingle(OGDMES_property,tmp)
		json_record[OGDMES_property] = sanityFirst(tmp)
		debug_output['31-OGDMES southBoundingLongitude'] = sanityFirst(tmp)

		##### OGDMES-32 northBoundingLongitude
		##################################################
		OGDMES_property = 'northBoundingLongitude'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal")
		sanitySingle(OGDMES_property,tmp)
		json_record[OGDMES_property] = sanityFirst(tmp)
		debug_output['32-OGDMES northBoundingLongitude'] = sanityFirst(tmp)

		GeoJSON = {}
		GeoJSON['type'] = "MultiPolygon"
		GeoJSON['coordinates'] = [[[
    		[json_record['westBoundingLongitude'], json_record['southBoundingLongitude']],
    		[json_record['eastBoundingLongitude'], json_record['southBoundingLongitude']],
    		[json_record['eastBoundingLongitude'], json_record['northBoundingLongitude']],
    		[json_record['westBoundingLongitude'], json_record['northBoundingLongitude']],
    		[json_record['westBoundingLongitude'], json_record['southBoundingLongitude']]
    	]]]

		json_record['spatial'] = GeoJSON
		#debug_output['32-OGDMES temporalElement'] = json_record['westBoundingLongitude']+','+json_record['eastBoundingLongitude']+','+json_record['northBoundingLongitude']+','+json_record['southBoundingLongitude']

		del json_record['westBoundingLongitude']
		del json_record['eastBoundingLongitude']
		del json_record['northBoundingLongitude']
		del json_record['southBoundingLongitude']

		##### OGDMES-33 temporalElement
		##################################################
		OGDMES_property = 'temporalElement'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition")
		sanitySingle(OGDMES_property,tmp)
		json_record['time_period_coverage_start'] = sanityFirst(tmp)
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition")
		sanitySingle(OGDMES_property,tmp)
		json_record['time_period_coverage_end'] = sanityFirst(tmp)

		debug_output['33-OGDMES temporalElement'] = json_record['time_period_coverage_start']+','+json_record['time_period_coverage_end']

		##### OGDMES-34 maintenanceAndUpdateFrequency
		##################################################
		OGDMES_property = 'maintenanceAndUpdateFrequency'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode")
		sanitySingle(OGDMES_property,tmp)
		json_record['frequency'] = {}
		if tmp == None or len(tmp) < 1:
			reportError(OGDMES_property+",no value,")
			json_record['frequency'][CKAN_primary_lang] = ''
			json_record['frequency'][CKAN_secondary_lang] = ''
		else:
			(primary,secondary) = sanityFirst(tmp).strip().split(';')
			json_record['frequency'][CKAN_primary_lang] = primary.strip()
			json_record['frequency'][CKAN_secondary_lang] = secondary.strip()

		debug_output['34-OGDMES maintenanceAndUpdateFrequency'+OGDMES_primary_lang] = json_record['frequency'][CKAN_primary_lang]
		debug_output['34-OGDMES maintenanceAndUpdateFrequency'+OGDMES_secondary_lang] = json_record['frequency'][CKAN_secondary_lang]

		##### OGDMES-35 licence_id
		##################################################
		OGDMES_property = 'licence_id'
		json_record['licence_id'] = 'what is the licence id for OGL, is it OGL?'

		debug_output['35-OGDMES LicenceEnglish'] = "Open Government Licence – Canada <linkto: http://open.canada.ca/en/open-government-licence-canada>"
		debug_output['35-OGDMES LicenceFrench'] = "Licence du gouvernement ouvert – Canada <linkto : http://ouvert.canada.ca/fr/licence-du-gouvernement-ouvert-canada>"

		##### OGDMES-36 referenceSystemInformation
		##################################################
		OGDMES_property = 'referenceSystemInformation'

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition")
		sanitySingle(OGDMES_property,tmp)
		vala = tmp[0]

		tmp = fetchXMLValues(record,"gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString")
		sanitySingle(OGDMES_property,tmp)
		valb = tmp[0]

		tmp = fetchXMLValues(record,"gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:version/gco:CharacterString")
		sanitySingle(OGDMES_property,tmp)
		valc = tmp[0]

		json_record['reference_system'] = '"'+vala+'","'+valb+'","'+valc+'"'

		debug_output['36-OGDMES referenceSystemInformation'] = json_record['reference_system']

		##### OGDMES-37 distributor
		##################################################
		OGDMES_property = 'distributor'

		primary_vals = []
		second_vals	= []

		tmp = fetchXMLValues(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString")
		sanitySingle(OGDMES_property,tmp)
		primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString")
		sanitySingle(OGDMES_property,tmp)
		primary_vals.append(sanityFirst(tmp))

		tmp = fetchXMLValues(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:organisationName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property,tmp)
		second_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_property,tmp)
		second_vals.append(sanityFirst(tmp))

		tmp = fetchXMLValues(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode")
		sanitySingle(OGDMES_property,tmp)
		singlePrime  = ''
		singleSecond = ''
		if tmp != None and len(tmp) > 0:
			(primary,secondary) = sanityFirst(tmp).strip().split(';')
			singlePrime = primary.strip()
			singleSecond = secondary.strip()
		role_array = []
		for (key,values) in napCI_RoleCode.items():
			if key == primary:
				role_array = values
				break
			if key == secondary:
				role_array = values
				break
		if len(role_array) < 2:
			print "ERROR: Distributor Bilingual Role"
		else:
			primary_vals.append(role_array[0])
			second_vals.append(role_array[1])

		json_record['distributor'] = {}
		json_record['distributor'][CKAN_primary_lang] = ','.join(primary_vals)
		json_record['distributor'][CKAN_secondary_lang] = ','.join(second_vals)

		debug_output['37-OGDMES distributor'+OGDMES_primary_lang] = json_record['distributor'][CKAN_primary_lang]
		debug_output['37-OGDMES distributor'+OGDMES_secondary_lang] = json_record['distributor'][CKAN_secondary_lang]

		##### OGDMES-38 CatalogueType
		##################################################
		OGDMES_property = 'CatalogueType'
		json_record['CatalogueType'] = 'geo or fgp?'
		debug_output['38-OGDMES CatalogueType'] = "geo or fgp?"

		record_resources = fetchXMLArray(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource")
		for resource in record_resources:
			json_record_resource = {}

			json_record_resource['ResourceName'] = {}

			tmp = fetchXMLValues(resource,"gmd:name/gco:CharacterString")
			sanitySingle(OGDMES_property,tmp)
			json_record_resource['ResourceName'][CKAN_primary_lang] = sanityFirst(tmp)
			debug_output['39-OGDMES CatalogueType'+OGDMES_primary_lang] = json_record_resource['ResourceName'][CKAN_primary_lang]

			tmp = fetchXMLValues(record,"gmd:name/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
			sanitySingle(OGDMES_property,tmp)
			json_record_resource['ResourceName'][CKAN_secondary_lang] = sanityFirst(tmp)
			debug_output['39-OGDMES CatalogueType'+OGDMES_secondary_lang] = json_record_resource['ResourceName'][CKAN_secondary_lang]

			tmp = fetchXMLValues(record,"gmd:linkage/gmd:URL")
			sanitySingle(OGDMES_property,tmp)
			json_record_resource['accessURL'] = sanityFirst(tmp)
			debug_output['40-OGDMES accessURL'] = json_record_resource['accessURL']

			tmp = fetchXMLValues(record,"gmd:description/gco:CharacterString")
			sanitySingle(OGDMES_property,tmp)
			if tmp == None or len(tmp) < 1:
				reportError(OGDMES_property+",format missing,")
				reportError(OGDMES_property+",language missing,")
				reportError(OGDMES_property+",contentType missing,")
				json_record_resource['format'] = ''
				json_record_resource['language'] = ''
				json_record_resource['contentType'] = ''
				debug_output['41-OGDMES format'] = ''
				debug_output['42-OGDMES language'] = ''
				debug_output['43-OGDMES contentType'] = ''
			else:
				(res_format,res_language,res_contentType) = sanityFirst(tmp).strip().split(';')
				json_record_resource['format'] = res_format.strip()
				json_record_resource['language'] = res_language.strip()
				json_record_resource['contentType'] = res_contentType.strip()
				debug_output['41-OGDMES format']
				debug_output['42-OGDMES language']
				debug_output['43-OGDMES contentType']

		continue

	print "DEBUG!"

	#debug_output = SortedDict(debug_output)	
	for key in sorted(debug_output):
		print key+':'+debug_output[key]

	if len(error_output) > 0:
		print "ERRORS!"
		sorted(error_output)
		for error in error_output:
			print error

	return 1

OGDMES2JSON = {}

OGDMES2ID                       = {
	'fileIdentifier'                :'01',
	'shortKey'                      :'02',
	'metadataRecordLanguage'        :'03',
	'characterSet'                  :'04',
	'parentIdentifier'              :'05',
	'hierarchyLevel'                :'06',
	'metadataContactEnglish'        :'07e',
	'metadataContactFrench'         :'07f',
	'metadataRecordDateStamp'       :'08',
	'metadataStandardName'          :'09',
	'metadataURI'                   :'10',
	'locale'                        :'11',
	'title english'                 :'12e',
	'title french'                  :'12f',
	'dateContributed'               :'13',
	'datePublished'                 :'14',
	'dateModified'                  :'15',
	'identifier'                    :'16',
	'individualName'                :'17',
	'organisationNameEnglish'       :'18e',
	'organisationNameFrench'        :'18f',
	'positionNameEnglish'           :'19e',
	'positionNameFrench'            :'19f',
	'contactInfoEnglish'            :'20e',
	'contactInfoFrench'             :'20f',
	'role'                          :'21',
	'abstractEnglish'               :'22e',
	'abstractFrench'                :'22f',
	'descriptiveKeywordsEnglish'    :'23e',
	'descriptiveKeywordsFrench'     :'23f',
	'status'                        :'24',
	'associationType'               :'25',
	'aggregateDataSetIdentifier'    :'26',
	'spatialRepresentationType'     :'27',
	'topicCategory'                 :'28',
	'westBoundingLongitude'         :'29',
	'eastBoundingLongitude'         :'30',
	'southBoundingLatitude'         :'31',
	'northBoundingLatitude'         :'32',
	'temporalElement'               :'33',
	'maintenanceAndUpdateFrequency' :'34',
	'licence'                       :'35',
	'referenceSystemInformation'    :'36',
	'distributorEnglish'            :'37e',
	'distributorFrench'             :'37f',
	'catalogueType'                 :'38',
	'ResourceNameEnglish'           :'39e',
	'ResourceNameFrench'            :'39f',
	'accessURL'                     :'40',
	'format'                        :'41',
	'language'                      :'42',
	'contentType'                   :'43'
}
	
	# Controled list
napCI_RoleCode                  = {
	'resourceProvider'              :['resourceProvider','fournisseurRessource'],
	'fournisseurRessource'          :['resourceProvider','fournisseurRessource'],
	'custodian'                     :['custodian','conservateur'],
	'conservateur'                  :['custodian','conservateur'],
	'owner'                         :['owner','propriétaire'],
	'propriétaire'                  :['owner','propriétaire'],
	'user'                          :['user','utilisateur'],
	'utilisateur'                   :['user','utilisateur'],
	'distributor'                   :['distributor','distributeur'],
	'distributeur'                  :['distributor','distributeur'],
	'pointOfContact'                :['pointOfContact','contact'],
	'contact'                       :['pointOfContact','contact'],
	'principalInvestigator'         :['principalInvestigator','chercheurPrincipal'],
	'chercheurPrincipal'            :['principalInvestigator','chercheurPrincipal'],
	'processor'                     :['processor','traiteur'],
	'traiteur'                      :['processor','traiteur'],
	'publisher'                     :['publisher','éditeur'],
	'éditeur'                       :['publisher','éditeur'],
	'author'                        :['author','auteur'],
	'auteur'                        :['author','auteur'],
	'collaborator'                  :['collaborator','collaborateur'],
	'collaborateur'                 :['collaborator','collaborateur'],
	'editor'                        :['editor','réviseur'],
	'réviseur'                      :['editor','réviseur'],
	'mediator'                      :['mediator','médiateur'],
	'médiateur'                     :['mediator','médiateur'],
	'rightsHolder'                  :['rightsHolder','détenteurDroits'],
	'détenteurDroits'               :['rightsHolder','détenteurDroits']
}

GC_Registry_of_Applied_Terms = [
	'Aboriginal Affairs and Northern Development Canada',
	'Agriculture and Agri-Food Canada',
	'Atlantic Canada Opportunities Agency',
	'Atlantic Pilotage Authority Canada',
	'Atomic Energy of Canada Limited',
	'Blue Water Bridge Canada',
	'Business Development Bank of Canada',
	'Canada Border Services Agency',
	'Canada Deposit Insurance Corporation',
	'Canada Development Investment Corporation',
	'Canada Emission Reduction Incentives Agency',
	'Canada Employment Insurance Commission',
	'Canada Employment Insurance Financing Board',
	'Canada Industrial Relations Board',
	'Canada Lands Company Limited',
	'Canada Mortgage and Housing Corporation',
	'Canada Post',
	'Canada Revenue Agency',
	'Canada School of Public Service',
	'Canada Science and Technology Museum',
	'Canadian Air Transport Security Authority',
	'Canadian Artists and Producers Professional Relations Tribunal',
	'Canadian Centre for Occupational Health and Safety',
	'Canadian Commercial Corporation',
	'Canadian Dairy Commission',
	'Canadian Environmental Assessment Agency',
	'Canadian Food Inspection Agency',
	'Canadian Forces Grievance Board',
	'Canadian Grain Commission',
	'Canadian Heritage',
	'Canadian Human Rights Commission',
	'Canadian Institutes of Health Research',
	'Canadian Intergovernmental Conference Secretariat',
	'Canadian International Development Agency',
	'Canadian International Trade Tribunal',
	'Canadian Museum for Human Rights',
	'Canadian Museum of Civilization',
	'Canadian Museum of Immigration at Pier 21',
	'Canadian Museum of Nature',
	'Canadian Northern Economic Development Agency',
	'Canadian Nuclear Safety Commission',
	'Canadian Polar Commission',
	'Canadian Radio-television and Telecommunications Commission',
	'Canadian Security Intelligence Service',
	'Canadian Space Agency',
	'Canadian Tourism Commission',
	'Canadian Transportation Agency',
	'Citizenship and Immigration Canada',
	'Commission for Public Complaints Against the Royal Canadian Mounted Police',
	'Communications Security Establishment Canada',
	'Copyright Board Canada',
	'Corporation for the Mitigation of Mackenzie Gas Project Impacts',
	'Correctional Service of Canada',
	'Courts Administration Service',
	'Defence Construction Canada',
	'Department of Finance Canada',
	'Department of Justice Canada',
	'Department of Social Development',
	'Economic Development Agency of Canada for the Regions of Quebec',
	'Elections Canada',
	'Enterprise Cape Breton Corporation',
	'Environment Canada',
	'Export Development Canada',
	'Farm Credit Canada',
	'Farm Products Council of Canada',
	'Federal Bridge Corporation',
	'Federal Economic Development Agency for Southern Ontario',
	'Financial Consumer Agency of Canada',
	'Financial Transactions and Reports Analysis Centre of Canada',
	'First Nations Statistical Institute',
	'Fisheries and Oceans Canada',
	'Foreign Affairs and International Trade Canada',
	'Freshwater Fish Marketing Corporation',
	'Great Lakes Pilotage Authority Canada',
	'Hazardous Materials Information Review Commission Canada',
	'Health Canada',
	'Human Resources and Skills Development Canada',
	'Human Rights Tribunal of Canada',
	'Immigration and Refugee Board of Canada',
	'Indian Residential Schools Truth and Reconciliation Commission',
	'Industry Canada',
	'Infrastructure Canada',
	'Laurentian Pilotage Authority Canada',
	'Law Commission of Canada',
	'Library and Archives Canada',
	'Library of Parliament',
	'Marine Atlantic Inc.',
	'Military Police Complaints Commission of Canada',
	'National Capital Commission',
	'National Defence',
	'National Energy Board',
	'National Film Board',
	'National Gallery of Canada',
	'National Research Council Canada',
	'National Round Table on the Environment and the Economy',
	'Natural Resources Canada',
	'Northern Pipeline Agency Canada',
	'Office of the Auditor General of Canada',
	'Office of the Commissioner for Federal Judicial Affairs Canada',
	'Office of the Commissioner of Lobbying of Canada',
	'Office of the Commissioner of Official Languages',
	'Office of the Communications Security Establishment Commissioner',
	'Office of the Public Sector Integrity Commissioner of Canada',
	'Office of the Secretary to the Governor General',
	'Office of the Superintendent of Financial Institutions Canada',
	'Offices of the Information and Privacy Commissioners of Canada',
	'Offices of the Information and Privacy Commissioners of Canada',
	'Pacific Pilotage Authority Canada',
	'Parks Canada',
	'Parole Board of Canada',
	'Patented Medicine Prices Review Board Canada',
	'Privy Council Office',
	'Public Health Agency of Canada',
	'Public Prosecution Service of Canada',
	'Public Safety Canada',
	'Public Servants Disclosure Protection Tribunal Canada',
	'Public Service Commission of Canada',
	'Public Service Labour Relations Board',
	'Public Service Staffing Tribunal',
	'Public Works and Government Services Canada',
	'RCMP External Review Committee',
	'Registrar of the Supreme Court of Canada and that portion of the federal public administration appointed under subsection 12(2) of the Supreme Court Act',
	'Registry of the Competition Tribunal',
	'Registry of the Specific Claims Tribunal of Canada',
	'Ridley Terminals Inc.',
	'Royal Canadian Mint',
	'Royal Canadian Mounted Police',
	'Science and Engineering Research Canada',
	'Security Intelligence Review Committee',
	'Shared Services Canada',
	'Social Sciences and Humanities Research Council of Canada',
	'Standards Council of Canada',
	'Statistics Canada',
	'Status of Women Canada',
	'The Correctional Investigator Canada',
	'The National Battlefields Commission',
	'Transport Canada',
	'Transportation Appeal Tribunal of Canada',
	'Transportation Safety Board of Canada',
	'Treasury Board',
	'Treasury Board of Canada Secretariat',
	'Veterans Affairs Canada',
	'Veterans Review and Appeal Board',
	'VIA Rail Canada Inc.',
	'Western Economic Diversification Canada',
	'Windsor-Detroit Bridge Authority'
]

if __name__    == "__main__":
	sys.exit(main())