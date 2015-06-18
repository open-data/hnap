#!/usr/bin/python
# -*- coding: utf-8 -*-

error_output   = []
debug_output   = {}

# Source Files an matching root

#input_file     = 'data/majechr_source.xml'
#records_root   = "/gmd:MD_Metadata"
input_file     = 'data/hnap_import.xml'
records_root   = "/csw:GetRecordsResponse/csw:SearchResults/gmd:MD_Metadata"

# Output files

output_json    = 'majechr_import.json'
output_jl      = 'majechr_import.jsonl'

source_hnap    = 'csw.open.canada.ca/csw?service=CSW&version=2.0.2&request=GetRecordById&outputSchema=csw:IsoRecord&id='

import time
iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

# Date validation
import datetime

import sys
import collections
import re
import json
import codecs

# XML Parsing
from lxml import etree

def fetchXMLArray(objectToXpath,xpath):
	return objectToXpath.xpath(xpath, namespaces={'gmd':'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco','gml':'http://www.opengis.net/gml/3.2','csw':'http://www.opengis.net/cat/csw/2.0.2'})
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
def fetchXMLAttribute(objectToXpath,xpath,attribute):
	# Easy to miss this, clean and combine
	clean_xpath     = xpath.rstrip('/')
	clean_attribute = xpath.lstrip('@')
	# Access to an attribute through lxml is
	# xpath/to/key/@key_attribute
	# e.g.:
	# html/body/@background-color
	return objectToXpath.xpath(xpath+'/@'+attribute, namespaces={'gmd':'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco','gml':'http://www.opengis.net/gml/3.2','csw':'http://www.opengis.net/cat/csw/2.0.2'})
def fetchCLValue(SRCH_key,CL_array):
	p = re.compile(' ')
	SRCH_key = SRCH_key.lower()
	SRCH_key = p.sub('', SRCH_key)
	for CL_key, value in CL_array.items():
		CL_key = CL_key.lower()
		CL_key = p.sub('', CL_key)
		CL_key = unicode(CL_key, errors='ignore')
		if SRCH_key == CL_key:
			return value
	return None
def reportError(errorText):
	global error_output
	global OGDMES2ID
	error_output.append(errorText)
def sanityMandatory(pre,values):
	values = list(set(values))
	if values == None or len(values) < 1:
		reportError(pre+',madatory field missing or not found in controlled list,""')
		return False
	return True
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
def sanityDate(pre,date_text):
	value = ''
	try:
		value = datetime.datetime.strptime(date_text, '%Y-%m-%d').isoformat().split('T')[0]
	except ValueError:
		reportError(pre+',date is not valid,"'+date_text+'"')
		return False
	if value != date_text:
		reportError(pre+',date is not valid,"'+date_text+'"')
		return False
	return True
def maskDate(date):
	#default_date = 
	if len(date) >= 10:
		return date
	return date+('xxxx-01-01'[-10+len(date):])

def main():
	# Read the file, should be a streamed input in the future
	root    = etree.parse(input_file)
	# Parse the root and itterate over each record
	records = 	fetchXMLArray(root,records_root)

	json_records = []
	for record in records:

		json_record  = {}
		debug_output = {}

		##### HNAP CORE LANGUAGE
		##################################################
		# Language is required, the rest can't be processed
		# for errors if the primary language is not certain
		OGDMES_property = 'HNAP_Language'
		tmp = fetchXMLValues(record,"gmd:language/gco:CharacterString")
		if False == sanitySingle('NOID,'+OGDMES_property,tmp):
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
		# A record ID is required, the rest can't be processed
		# for errors if the primary language is not certain
		OGDMES_property = 'fileIdentifier'
		tmp = fetchXMLValues(record,"gmd:fileIdentifier/gco:CharacterString")
		if False == sanitySingle('NOID,'+OGDMES_property,tmp):
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

		# From here on in continue if you can and collect as many errors as
		# possible for FGP Help desk.  We awant to had a full report of issues
		# to correct, not one error at a time.
		# It's faster for them to correct a batch of errors in parallel as
		# opposed to doing them piecemeal.
		
		##### OGDMES-02 shortKey
		##################################################
		# Shortkey is not defined in HNAP, it will eventually be required
		# as collisions will happen when there are significantly more
		# records.  When that happens shortkeys will need to be provided
		# and the XPATH will need to be offered and used first.  The logic
		# will be 1) if offered use the provided shortkey 2) if not offered
		# use this math derived shortkey.
		OGDMES_property = 'shortKey'
		json_record['name'] = OGDMES_fileIdentifier[0:8]
		debug_output['02-OGDMES shortKey [calculated]'] = OGDMES_fileIdentifier[0:8]

		##### OGDMES-03 metadataRecordLanguage
		##################################################
		# This is presently the same as the the core HNAP language but this
		# OGDMES property may dissapear, it was included prior to the
		# knowledge that the HNAP record was bilingual
		OGDMES_property = 'metadataRecordLanguage'
		#Ian Ward @ CKAN:disable:json_record[OGDMES_property] = HNAP_primary_language
		debug_output['03-OGDMES metadataRecordLanguage'] = HNAP_primary_language

		##### OGDMES-04 characterSet
		##################################################
		OGDMES_property = 'characterSet'
		tmp = fetchXMLValues(record,"gmd:characterSet/gmd:MD_CharacterSetCode")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
		#Ian Ward @ CKAN:disable:json_record[OGDMES_property] = sanityFirst(tmp).split(';')[0]
			debug_output['04-OGDMES characterSet'] = sanityFirst(tmp).split(';')[0]

		##### OGDMES-05 parentIdentifier
		##################################################
		OGDMES_property = 'parentIdentifier'
		tmp = fetchXMLValues(record,"gmd:parentIdentifier/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		json_record['parent_id'] = sanityFirst(tmp)
		debug_output['05-OGDMES parentIdentifier'] = sanityFirst(tmp)

		##### OGDMES-06 hierarchyLevel
		##################################################
		OGDMES_property = 'hierarchyLevel'
		tmp = fetchXMLValues(record,"gmd:hierarchyLevel/gmd:MD_ScopeCode")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			(primary,secondary) = sanityFirst(tmp).strip().split(';')			
			json_record['hierarchy_level'] = primary.strip()
			debug_output['06-OGDMES hierarchyLevel'] = json_record['hierarchy_level']

		##### OGDMES-07 metadataContact
		##################################################
		OGDMES_property = 'metadataContact'
		primary_vals = []
		second_vals = []

		# organizationName
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-OrganizationName-'+CKAN_primary_lang,tmp):
			primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:organisationName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-OrganizationName-'+CKAN_secondary_lang,tmp):
			second_vals.append(sanityFirst(tmp))

		# voice
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString")
		for value in tmp:
			primary_vals.append(value)
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		for value in tmp:
			second_vals.append(value)

#		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString")
#		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang,tmp)
#		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-Voice-'+CKAN_primary_lang,tmp):
#			primary_vals.append(sanityFirst(tmp))
#		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
#		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang,tmp)
#		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-Voice-'+CKAN_secondary_lang,tmp):
#			second_vals.append(sanityFirst(tmp))

		# electronicMailAddress
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-electronicMailAddress-'+CKAN_primary_lang,tmp):
			primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-electronicMailAddress-'+CKAN_secondary_lang,tmp):
			second_vals.append(sanityFirst(tmp))

		json_record['metadata_contact'] = {}
		json_record['metadata_contact'][CKAN_primary_lang] = ','.join(primary_vals)
		json_record['metadata_contact'][CKAN_secondary_lang] = ','.join(second_vals)

		debug_output['07-OGDMES metadataContact'+OGDMES_primary_lang] = json_record['metadata_contact'][CKAN_primary_lang]
		debug_output['07-OGDMES metadataContact'+OGDMES_secondary_lang] = json_record['metadata_contact'][CKAN_secondary_lang]

		##### OGDMES-08 metadataRecordDateStamp
		##################################################
		OGDMES_property = 'metadataRecordDateStamp'
		tmp = fetchXMLValues(record,"gmd:dateStamp/gco:Date")

		values = list(set(tmp))
		if len(values) < 1:
			tmp = fetchXMLValues(record,"gmd:dateStamp/gco:DateTime")

		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):

			# Might be a iso datetime
			date_str = sanityFirst(tmp)
			if date_str.count('T') == 1:
				date_str = date_str.split('T')[0]

			if sanityDate(OGDMES_fileIdentifier+','+OGDMES_property,date_str):
				json_record['characterSet'] = date_str
				debug_output['08-OGDMES metadataRecordDateStamp'] = date_str

		##### OGDMES-09 metadataStandardName
		##################################################
		#Ian Ward @ CKAN:disable:json_record['metadataStandardName'] = {}
		#Ian Ward @ CKAN:disable:json_record['metadataStandardName']['en'] = 'Government of Canada’s Open Geospatial Data Metadata Element Set'
		#Ian Ward @ CKAN:disable:json_record['metadataStandardName']['fr'] = 'Données ouvertes géospatiales du gouvernement du Canada – Ensemble d’éléments de métadonnées'
		debug_output['09-OGDMES metadataStandardNameEnglish'] = 'Government of Canada’s Open Geospatial Data Metadata Element Set'
		debug_output['09-OGDMES metadataStandardNameFrench'] = 'Données ouvertes géospatiales du gouvernement du Canada – Ensemble d’éléments de métadonnées'

		##### OGDMES-10 metadataURI
		##################################################
		json_record['url'] = source_hnap+OGDMES_fileIdentifier
		debug_output['10-OGDMES metadataURI'] = json_record['url']

		##### OGDMES-11 locale
		##################################################
		OGDMES_property = 'locale'
		tmp = fetchXMLAttribute(record,"gmd:locale/gmd:PT_Locale/gmd:languageCode/gmd:LanguageCode","codeListValue")

		if tmp != None and len(tmp) > 0:
			#Ian Ward @ CKAN:disable:json_record[OGDMES_property][CKAN_primary_lang] = ','.join(primary_vals)
			#Ian Ward @ CKAN:disable:json_record[OGDMES_property][CKAN_secondary_lang] = ','.join(second_vals)
			debug_output['11-OGDMES locale'] = tmp[0]

		##### OGDMES-12 title
		##################################################
		OGDMES_property = 'title'
		json_record[OGDMES_property] = {}

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			json_record[OGDMES_property][CKAN_primary_lang] = sanityFirst(tmp)
			debug_output['12-OGDMES title'+OGDMES_primary_lang] = json_record[OGDMES_property][CKAN_primary_lang]
		
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			json_record[OGDMES_property][CKAN_secondary_lang] = sanityFirst(tmp)
			debug_output['12-OGDMES title'+OGDMES_secondary_lang] = json_record[OGDMES_property][CKAN_secondary_lang]

		##### OGDMES-13 dateContributed
		##################################################
		OGDMES_property = 'dateContributed'
		#Ian Ward @ CKAN:disable:json_record[OGDMES_property] = {}
		debug_output['13-OGDMES dateContributed'] = '[CKAN SUPPLIED]'

		##### OGDMES-14 datePublished
		##### OGDMES-15 dateModified
		##################################################
		# This one is a little different, we have to do this bad boy manually
		#r = record.xpath("gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date", namespaces={'gmd':'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco'})
		r = record.xpath("gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date", namespaces={'gmd':'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco'})
		if(len(r)):
			for cn in r:
				input_types = {}
				inKey = []
				inVal = ''
				# Decypher which side has the code and which has the data, yea... it changes -sigh-
				# Keys will always use the ;
				if len(cn[0][0].text.split(';')) > 1:
					inKey = cn[0][0].text.split(';')
					inVal = cn[1][0].text.strip()
				else:
					inKey = cn[1][0].text.split(';')
					inVal = cn[0][0].text.strip()

				for input_type in inKey:
					input_type = input_type.strip()
					#print "TYPE:"+input_type
					if input_type == u'publication':
						if sanityDate(OGDMES_fileIdentifier+',date_published',inVal):
							json_record['date_published'] = inVal
							debug_output['14-OGDMES date_published'] = json_record['date_published']
							break

					if input_type == u'revision' or input_type == u'révision':
						if sanityDate(OGDMES_fileIdentifier+',date_modified',inVal):
							json_record['date_modified'] = inVal
							debug_output['15-OGDMES date_modified'] = json_record['date_modified']
							break

		if 'date_published' not in json_record:
			reportError(OGDMES_fileIdentifier+','+'datePublished,madatory field missing,""')

		##### OGDMES-16 identifier
		##################################################
		OGDMES_property = 'identifier'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		json_record['digital_object_identifier'] = sanityFirst(tmp)
		debug_output['16-OGDMES identifier'] = sanityFirst(tmp)

		##### OGDMES-17 individualName
		##################################################
		OGDMES_property = 'individualName'
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:individualName/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
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
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_primary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_primary_lang,tmp):		
			values = tmp[0].strip().split(';')
			if values[0] != 'Government of Canada' and values[0] != 'Gouvernement du Canada':
				reportError(OGDMES_fileIdentifier+','+organisationName+',"Bad organizationName, no Government of Canada",""')
			del values[0]
			# At ths point you have ditched GOC and your checking for good dept names
			for GOC_Div in values:
				# Are they in the CL?
				termsValue = fetchCLValue(GOC_Div,GC_Registry_of_Applied_Terms)
				if termsValue:
					if CKAN_primary_lang == 'en':
						primary_vals.append(termsValue[0]) # Use CL value, cleaner and more consistent
					else:
						primary_vals.append(termsValue[2]) # Use CL value, cleaner and more consistent
			
			if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_primary_lang,primary_vals):
				json_record['responsible_organization'][CKAN_primary_lang] = ','.join(primary_vals)
				debug_output['18-OGDMES organisationName'+OGDMES_primary_lang] = json_record['responsible_organization'][CKAN_primary_lang]

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty/gmd:organisationName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_secondary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_secondary_lang,tmp):
			values = tmp[0].strip().split(';')
			if values[0] != 'Government of Canada' and values[0] != 'Gouvernement du Canada':
				reportError(organisationName+',"Bad organizationName, no Government of Canada",""')
			del values[0]
			for GOC_Div in values:
				#print "FRGOC_DIV:"+GOC_Div
				termsValue = fetchCLValue(GOC_Div,GC_Registry_of_Applied_Terms)
				if termsValue:
					if CKAN_primary_lang == 'en':
						second_vals.append(termsValue[2])
					else:
						second_vals.append(termsValue[0])

			if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_secondary_lang,second_vals):
				json_record['responsible_organization'][CKAN_secondary_lang] = ','.join(second_vals)
				debug_output['18-OGDMES organisationName'+OGDMES_secondary_lang] = json_record['responsible_organization'][CKAN_secondary_lang]

		##### OGDMES-19 positionName
		##################################################
		OGDMES_property = 'positionName'
		json_record['position_name'] = {}
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:positionName/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		json_record['position_name'][CKAN_primary_lang] = sanityFirst(tmp)
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:positionName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		json_record['position_name'][CKAN_secondary_lang] = sanityFirst(tmp)
		
		debug_output['19-OGDMES positionName'+OGDMES_primary_lang] = json_record['position_name'][CKAN_primary_lang]
		debug_output['19-OGDMES positionName'+OGDMES_secondary_lang] = json_record['position_name'][CKAN_secondary_lang]

		##### OGDMES-20 contactInfo
		##################################################
		OGDMES_property = 'contactInfo'

		primary_vals = []
		second_vals	= []

		json_record['contactInfo'] = {}
		json_record['contactInfo'][CKAN_primary_lang] = {}
		json_record['contactInfo'][CKAN_secondary_lang] = {}

		tkey = 'deliveryPoint'
		json_record['contactInfo'][CKAN_primary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:deliveryPoint/gco:CharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_primary_lang][tkey] = sanityFirst(tmp)
			primary_vals.append(sanityFirst(tmp))
		tkey = 'city'
		json_record['contactInfo'][CKAN_primary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:city/gco:CharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_primary_lang][tkey] = sanityFirst(tmp)
			primary_vals.append(sanityFirst(tmp))
		tkey = 'administrativeArea'
		json_record['contactInfo'][CKAN_primary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:administrativeArea/gco:CharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_primary_lang][tkey] = sanityFirst(tmp)
			primary_vals.append(sanityFirst(tmp))
		tkey = 'postalCode'
		json_record['contactInfo'][CKAN_primary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:postalCode/gco:CharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_primary_lang][tkey] = sanityFirst(tmp)
			primary_vals.append(sanityFirst(tmp))
		tkey = 'country'
		json_record['contactInfo'][CKAN_primary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:country/gco:CharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_primary_lang][tkey] = sanityFirst(tmp)
			primary_vals.append(sanityFirst(tmp))
		tkey = 'electronicMailAddress'
		json_record['contactInfo'][CKAN_primary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_primary_lang][tkey] = sanityFirst(tmp)
			primary_vals.append(sanityFirst(tmp))


		tkey = 'deliveryPoint'
		json_record['contactInfo'][CKAN_secondary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:deliveryPoint/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_secondary_lang][tkey] = sanityFirst(tmp)
			second_vals.append(sanityFirst(tmp))
		tkey = 'city'
		json_record['contactInfo'][CKAN_secondary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:city/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_secondary_lang][tkey] = sanityFirst(tmp)
			second_vals.append(sanityFirst(tmp))
		tkey = 'administrativeArea'
		json_record['contactInfo'][CKAN_secondary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:administrativeArea/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_secondary_lang][tkey] = sanityFirst(tmp)
			second_vals.append(sanityFirst(tmp))
		tkey = 'postalCode'
		json_record['contactInfo'][CKAN_secondary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:postalCode/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_secondary_lang][tkey] = sanityFirst(tmp)
			second_vals.append(sanityFirst(tmp))
		tkey = 'country'
		json_record['contactInfo'][CKAN_secondary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:country/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_secondary_lang][tkey] = sanityFirst(tmp)
			second_vals.append(sanityFirst(tmp))
		tkey = 'electronicMailAddress'
		json_record['contactInfo'][CKAN_secondary_lang][tkey] = ''
		tmp = fetchXMLValues(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang+tkey,tmp):
			json_record['contactInfo'][CKAN_secondary_lang][tkey] = sanityFirst(tmp)
			second_vals.append(sanityFirst(tmp))

		if not len(primary_vals):
			reportError(OGDMES_fileIdentifier+','+'contactInfo,madatory field missing,""')
		if not len(second_vals):
			reportError(OGDMES_fileIdentifier+','+'contactInfo,madatory field missing,""')

		debug_output['20-OGDMES contactInfo'+OGDMES_primary_lang] = ','.join(primary_vals)
		debug_output['20-OGDMES contactInfo'+OGDMES_secondary_lang] = ','.join(second_vals)

		##### OGDMES-21 role
		##################################################
		OGDMES_property = 'role'
		tmp = fetchXMLAttribute(record,"gmd:contact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode","codeListValue")
		json_record['responsible_role'] = {}
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
				# Can you find the CL entry?
				termsValue = fetchCLValue(tmp[0],napCI_RoleCode)
				if not termsValue:
					termsValue = []
				if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,termsValue):
					json_record['responsible_role'] = termsValue[0]
					debug_output['21-OGDMES responsible_role'] = json_record['responsible_role']

		##### OGDMES-22 abstract
		##################################################
		OGDMES_property = 'abstract'
		json_record['notes'] = {}

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_primary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			json_record['notes'][CKAN_primary_lang] = sanityFirst(tmp)
			debug_output['22-OGDMES abstract'+OGDMES_primary_lang] = json_record['notes'][CKAN_primary_lang]
		
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+CKAN_secondary_lang,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			json_record['notes'][CKAN_secondary_lang] = sanityFirst(tmp)
			debug_output['22-OGDMES abstract'+OGDMES_secondary_lang] = json_record['notes'][CKAN_secondary_lang]

		##### OGDMES-23 descriptiveKeywords
		##################################################
#
#
#  ERROR: ITTERATE OVER EACH 
#  gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/
#
#  THEN:
#  gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/
#
#
		OGDMES_property = 'descriptiveKeywords'
		json_record['keywords'] = {}
		primary_vals = []
		second_vals	= []
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString")
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_primary_lang,tmp):
			for value in tmp:
				p = re.compile('^[A-Z][A-Z] [^>]+ > ')
				value = p.sub( '', value)
				if len(value) >= 2:
					primary_vals.append(value)
			if not len(primary_vals):
				reportError(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_primary_lang+',""')

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_secondary_lang,tmp):
			for value in tmp:
				p = re.compile('^[A-Z][A-Z] [^>]+ > ')
				value = p.sub( '', value)
				if len(value) >= 2:
					second_vals.append(value)
			if not len(second_vals):
				reportError(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_secondary_lang+',""')

		json_record['keywords'][CKAN_primary_lang] = primary_vals
		json_record['keywords'][CKAN_secondary_lang] = second_vals
		debug_output['23-OGDMES descriptiveKeywords'+OGDMES_primary_lang] = ','.join(primary_vals)
		debug_output['23-OGDMES descriptiveKeywords'+OGDMES_secondary_lang] = ','.join(second_vals)

		##### OGDMES-24 status
		##################################################
		OGDMES_property = 'status'
		tmp = fetchXMLAttribute(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode","codeListValue")
		json_record[OGDMES_property] = {}
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
				# Can you find the CL entry?
				termsValue = fetchCLValue(tmp[0],napMD_ProgressCode)
				if not termsValue:
					termsValue = []
				if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,termsValue):
					json_record[OGDMES_property] = termsValue[0]
					debug_output['24-OGDMES status'] = json_record[OGDMES_property]

		##### OGDMES-25 associationType
		##################################################
		OGDMES_property = 'associationType'

		tmp = fetchXMLAttribute(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:aggregationInfo/gmd:MD_AggregateInformation/gmd:associationType/gmd:DS_AssociationTypeCode","codeListValue")
		associationTypes_array = []
		# Not mandatory, process if you have it
		if tmp != None and len(tmp) > 0:
			# You have to itterate to find a valid one, not neccesaraly the first
			for associationType in tmp:
				# Can you find the CL entry?
				termsValue = fetchCLValue(associationType,napDS_AssociationTypeCode)
				if not termsValue:
					termsValue = []
				if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,termsValue):
					associationTypes_array.append(termsValue[0])					
		json_record['association_type'] = ','.join(associationTypes_array)
		debug_output['25-OGDMES associationType'] = json_record['association_type']

		##### OGDMES-26 aggregateDataSetIdentifier
		##################################################
		# No test data but this XPATH bas been confirmed by Marie-Eve Martin @ NRCan
		OGDMES_property = 'aggregateDataSetIdentifier'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:aggregationInfo/gmd:MD_AggregateInformation/gmd:aggregateDataSetIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)

		aggregateDataSetIdentifier_array = []

		if tmp != None and len(tmp) > 0:
			for aggregateDataSetIdentifier in tmp:
				(primary,secondary) = aggregateDataSetIdentifier.strip().split(';')
				aggregateDataSetIdentifier_array.append(primary.strip())
				aggregateDataSetIdentifier_array.append(secondary.strip())

		json_record['aggregate_identifier'] = ','.join(aggregateDataSetIdentifier_array)
		debug_output['26-OGDMES aggregateDataSetIdentifier'] = json_record['aggregate_identifier']

		##### OGDMES-27 spatialRepresentationType
		##################################################
		OGDMES_property = 'spatialRepresentationType'

		tmp = fetchXMLAttribute(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialRepresentationType/gmd:MD_SpatialRepresentationTypeCode","codeListValue")
		json_record['spatial_representation_type'] = {}
		spatialRepresentationType_array = []

		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			# You have to itterate to find a valid one, not neccesaraly the first
			for spatialRepresentationType in tmp:
				# Can you find the CL entry?
				termsValue = fetchCLValue(spatialRepresentationType,napMD_SpatialRepresentationTypeCode)
				if not termsValue:
					termsValue = []
				if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,termsValue):
					json_record[OGDMES_property] = termsValue[0]
					debug_output['27-OGDMES spatialRepresentationType'] = json_record[OGDMES_property]

				if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,termsValue):
					spatialRepresentationType_array.append(termsValue[0])

		json_record['spatial_representation_type'] = ','.join(spatialRepresentationType_array)
		debug_output['27-OGDMES spatialRepresentationType'] = json_record['spatial_representation_type']


		##### OGDMES-28 topicCategory
		##################################################
		OGDMES_property = 'topicCategory'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode")
		#sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		
		topicCategory_array = []

		# There has to be the field, filled
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			for topicCategory in tmp:
				termsValue = fetchCLValue(topicCategory.strip(),napMD_KeywordTypeCode)
				if termsValue:
					topicCategory_array.append(topicCategory)

			# After we check aganst the CL we need to make sure thre still is data before you accept it
			if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,topicCategory_array):
				json_record['topic_category'] = topicCategory_array
				debug_output['28-OGDMES topicCategory'] = ','.join(topicCategory_array)

		##### OGDMES-29 westBoundingLongitude
		##################################################
		OGDMES_property = 'westBoundingLongitude'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			json_record[OGDMES_property] = sanityFirst(tmp)
			debug_output['29-OGDMES westBoundingLongitude'] = sanityFirst(tmp)

		##### OGDMES-30 eastBoundingLongitude
		##################################################
		OGDMES_property = 'eastBoundingLongitude'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			json_record[OGDMES_property] = sanityFirst(tmp)
			debug_output['30-OGDMES eastBoundingLongitude'] = sanityFirst(tmp)

		##### OGDMES-31 southBoundingLongitude
		##################################################
		OGDMES_property = 'southBoundingLongitude'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			json_record[OGDMES_property] = sanityFirst(tmp)
			debug_output['31-OGDMES southBoundingLongitude'] = sanityFirst(tmp)

		##### OGDMES-32 northBoundingLongitude
		##################################################
		OGDMES_property = 'northBoundingLongitude'
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			json_record[OGDMES_property] = sanityFirst(tmp)
			debug_output['32-OGDMES northBoundingLongitude'] = sanityFirst(tmp)

		GeoJSON = {}
		GeoJSON['type'] = "Polygon"
		GeoJSON['coordinates'] = [[
    		[float(json_record['westBoundingLongitude']), float(json_record['southBoundingLongitude'])],
    		[float(json_record['eastBoundingLongitude']), float(json_record['southBoundingLongitude'])],
    		[float(json_record['eastBoundingLongitude']), float(json_record['northBoundingLongitude'])],
    		[float(json_record['westBoundingLongitude']), float(json_record['northBoundingLongitude'])],
    		[float(json_record['westBoundingLongitude']), float(json_record['southBoundingLongitude'])]
    	]]

		json_record['spatial'] = GeoJSON
		#debug_output['32-OGDMES temporalElement'] = json_record['westBoundingLongitude']+','+json_record['eastBoundingLongitude']+','+json_record['northBoundingLongitude']+','+json_record['southBoundingLongitude']

		# The GeoJSON covers these, ditch them.
		del json_record['westBoundingLongitude']
		del json_record['eastBoundingLongitude']
		del json_record['northBoundingLongitude']
		del json_record['southBoundingLongitude']

		##### OGDMES-33 temporalElement
		##################################################
		OGDMES_property = 'temporalElement'
		temporalElement_array = []
		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition")
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'Start',tmp):
			if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+'Start',tmp):
				if sanityDate(OGDMES_fileIdentifier+','+OGDMES_property+'Start',maskDate(sanityFirst(tmp))):
						json_record['time_period_coverage_start'] = maskDate(sanityFirst(tmp))
						temporalElement_array.append(json_record['time_period_coverage_start'])

		tmp = fetchXMLValues(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+'End',tmp)
		# ADAPTATION #2
		# CKAN (or Solr) requires an end date where one doesn't exist.  An open record should run
		# without an end date.  Since this is not the case a '9999-99-99' is used in lieu.
		# ADAPTATION #3
		# Temporal elements are ISO 8601 date objects but this field may be left blank (invalid).
		# The intent is to use a blank field as a maker for an "open" record were omission of this
		# field would be standard practice.  No gml:endPosition = no end.
		# Since changing the source seems to be impossible we adapt by replacing a blank entry with
		# the equally ugly '9999-99-99' forced end in CKAN.
		check_for_blank = sanityFirst(tmp)
		if check_for_blank == '':
			check_for_blank = '9999-09-09'
		if check_for_blank == '9999-09-09' or sanityDate(OGDMES_fileIdentifier+','+OGDMES_property+'End',maskDate(check_for_blank)):
			json_record['time_period_coverage_end'] = maskDate(check_for_blank)
			temporalElement_array.append(json_record['time_period_coverage_end'])
		## End ADAPTATION #2 & #3

		debug_output['33-OGDMES temporalElement'] = ','.join(temporalElement_array)

		##### OGDMES-34 maintenanceAndUpdateFrequency
		##################################################
		OGDMES_property = 'maintenanceAndUpdateFrequency'

		tmp = fetchXMLAttribute(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode","codeListValue")
		json_record['frequency'] = {}
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
				# Can you find the CL entry?
				termsValue = fetchCLValue(tmp[0],napMD_MaintenanceFrequencyCode)
				if not termsValue:
					termsValue = []
				if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,termsValue):
					json_record['frequency'] = termsValue[0]
					debug_output['34-OGDMES maintenanceAndUpdateFrequency'] = json_record['frequency']

		##### OGDMES-35 licence_id
		##################################################
		OGDMES_property = 'licence_id'
		json_record['license_id'] = 'ca-ogl-lgo'
		debug_output['35-OGDMES Licence'] = "Open Government Licence – Canada <linkto: http://open.canada.ca/en/open-government-licence-canada>"

		data_constraints = fetchXMLArray(record,"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints")
		licence_count    = 0
		for data_constraint in data_constraints:
			accessConstraint = False
			useConstraint    = False
			tmp = fetchXMLAttribute(data_constraint,"gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode","codeListValue")
			if len(tmp) and tmp[0] == 'RI_606': # RI_606 is a licence
				accessConstraint = True
			tmp = fetchXMLAttribute(data_constraint,"gmd:MD_LegalConstraints/gmd:useConstraints/gmd:MD_RestrictionCode","codeListValue")
			if len(tmp) and tmp[0] == 'RI_606': # RI_606 is a licence
				useConstraint = True

			if accessConstraint == True or useConstraint == True:
				licence_count += 1

				tmp = fetchXMLValues(data_constraint,"gmd:MD_LegalConstraints/gmd:useLimitation/gco:CharacterString")
				if sanityMandatory(OGDMES_property+','+OGDMES_property,tmp):	
					if sanityFirst(tmp).strip() != 'Open Government Licence - Canada (http://open.canada.ca/en/open-government-licence-canada)':
						reportError(OGDMES_fileIdentifier+','+'license,Invalid License,"'+str(tmp)+'"')

				tmp = fetchXMLValues(data_constraint,"gmd:MD_LegalConstraints/gmd:useLimitation/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
				if sanityMandatory(OGDMES_property+','+OGDMES_property,tmp):	
					if sanityFirst(tmp).strip() != 'Licence du gouvernement ouvert - Canada (http://ouvert.canada.ca/fr/licence-du-gouvernement-ouvert-canada)':
						reportError(OGDMES_fileIdentifier+','+'license,Invalid License,"'+str(tmp)+'"')
		if licence_count > 1:
			reportError(OGDMES_fileIdentifier+','+'license,More than one licence,""')

		##### OGDMES-36 referenceSystemInformation
		##################################################
		OGDMES_property = 'referenceSystemInformation'

		vala = valb = valc = ''

		tmp = fetchXMLValues(record,"gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			vala = tmp[0]
		tmp = fetchXMLValues(record,"gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			valb = tmp[0]
		tmp = fetchXMLValues(record,"gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:version/gco:CharacterString")
		sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
			valc = tmp[0]
		json_record['reference_system'] = vala+','+valb+','+valc
		debug_output['36-OGDMES referenceSystemInformation'] = json_record['reference_system']

		##### OGDMES-37 distributor
		##################################################
		OGDMES_property = 'distributor'

		primary_vals = []
		second_vals	= []

		OGDMES_subproperty = 'organizationName'
		tmp = fetchXMLValues(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString")
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty+OGDMES_primary_lang,tmp):
			if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty+OGDMES_primary_lang,tmp):
				primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:organisationName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty+OGDMES_secondary_lang,tmp):
			if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty+OGDMES_secondary_lang,tmp):
				second_vals.append(sanityFirst(tmp))

		OGDMES_subproperty = 'electronicMailAddress'
		tmp = fetchXMLValues(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString")
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty+OGDMES_primary_lang,tmp):
			if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty+OGDMES_primary_lang,tmp):
				primary_vals.append(sanityFirst(tmp))
		tmp = fetchXMLValues(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty+OGDMES_secondary_lang,tmp):
			if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty+OGDMES_secondary_lang,tmp):
				second_vals.append(sanityFirst(tmp))

		OGDMES_subproperty = 'role'
		tmp = fetchXMLAttribute(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode","codeListValue")
		if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty,tmp):
			if sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty,tmp):
				# Can you find the CL entry?
				termsValue = fetchCLValue(tmp[0],napCI_RoleCode)
				if not termsValue:
					termsValue = []
				if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+'-'+OGDMES_subproperty,termsValue):
					primary_vals.append(termsValue[0])
					second_vals.append(termsValue[1])

		json_record['distributor'] = {}
		json_record['distributor'][CKAN_primary_lang] = ','.join(primary_vals)
		json_record['distributor'][CKAN_secondary_lang] = ','.join(second_vals)

		debug_output['37-OGDMES distributor'+OGDMES_primary_lang] = json_record['distributor'][CKAN_primary_lang]
		debug_output['37-OGDMES distributor'+OGDMES_secondary_lang] = json_record['distributor'][CKAN_secondary_lang]

		##### OGDMES-38 CatalogueType
		##################################################
		OGDMES_property = 'CatalogueType'
		#Ian Ward @ CKAN:disable:json_record['type'] = 'Open Maps / Cartes ouvert'
		json_record['type'] = 'maps'
		debug_output['38-OGDMES CatalogueType'] = json_record['type']

		##### OGDMES-39 ResourceNameEnglish
		##################################################
		##### OGDMES-40 accessURL
		##################################################
		##### OGDMES-41 format
		##################################################
		##### OGDMES-42 language
		##################################################
		##### OGDMES-43 contentType
		##################################################
		json_record['resources'] = []
		record_resources = fetchXMLArray(record,"gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource")
		
		resource_no = 0
		for resource in record_resources:
			resource_no += 1

			json_record_resource = {}
			json_record_resource['name'] = {}

			OGDMES_property = 'Resource['+str(resource_no)+']-ResourceName'
			tmp = fetchXMLValues(resource,"gmd:name/gco:CharacterString")
			sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
			if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_primary_lang,tmp):
				json_record_resource['name'][CKAN_primary_lang] = sanityFirst(tmp)
				debug_output['39-OGDMES Resource['+str(resource_no)+'] ResourceName'+OGDMES_primary_lang] = sanityFirst(tmp)

			tmp = fetchXMLValues(resource,"gmd:name/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
			sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
			if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property+OGDMES_secondary_lang,tmp):
				json_record_resource['name'][CKAN_secondary_lang] = sanityFirst(tmp)
				debug_output['39-OGDMES Resource['+str(resource_no)+'] ResourceName'+OGDMES_secondary_lang] = sanityFirst(tmp)

			OGDMES_property = 'Resource['+str(resource_no)+']-accessUrl'
			tmp = fetchXMLValues(resource,"gmd:linkage/gmd:URL")
			sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
			if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
				json_record_resource['url'] = sanityFirst(tmp)
				debug_output['40-OGDMES Resource['+str(resource_no)+'] accessURL'] = sanityFirst(tmp)

			OGDMES_property = 'Resource['+str(resource_no)+']-description;'
			tmp = fetchXMLValues(resource,"gmd:description/gco:CharacterString")
			sanitySingle(OGDMES_fileIdentifier+','+OGDMES_property,tmp)
			if sanityMandatory(OGDMES_fileIdentifier+','+OGDMES_property,tmp):
				description_text = sanityFirst(tmp).strip()
				#print "PREUNPACK:"+OGDMES_fileIdentifier+":"+description_text
				if description_text.count(';') != 2:
					reportError(OGDMES_fileIdentifier+','+OGDMES_property+'contentType,"Error with source, should be contentType;format;lang,lang","'+description_text+'"')
					reportError(OGDMES_fileIdentifier+','+OGDMES_property+'format,"Error with source, should be contentType;format;lang,lang","'+description_text+'"')
					reportError(OGDMES_fileIdentifier+','+OGDMES_property+'languages,"Error with source, should be contentType;format;lang,lang","'+description_text+'"')
					debug_output['41-OGDMES Resource['+str(resource_no)+'] format'] = 'err'
					debug_output['42-OGDMES Resource['+str(resource_no)+'] language'] = 'err'
					debug_output['43-OGDMES Resource['+str(resource_no)+'] contentType'] = 'err'
				else:
					(res_contentType,res_format,res_language) = description_text.split(';')

					languages_in  = res_language.strip().split(',')
					languages_out = []
					for language in languages_in:
						if language.strip() == 'eng':
							languages_out.append('eng; CAN')
						if language.strip() == 'fra':
							languages_out.append('fra; CAN')
					#language_str = ','.join(languages_out)
					language_str = languages_out[0]

					json_record_resource['format'] = res_format.strip()
					json_record_resource['language'] = language_str
					json_record_resource['contentType'] = res_contentType.strip()
					debug_output['41-OGDMES Resource['+str(resource_no)+'] format'] = res_format.strip()
					debug_output['42-OGDMES Resource['+str(resource_no)+'] language'] = language_str
					debug_output['43-OGDMES Resource['+str(resource_no)+'] contentType'] = res_contentType.strip()
			else:
				reportError(OGDMES_fileIdentifier+','+OGDMES_property+'format,madatory field missing,""')
				reportError(OGDMES_fileIdentifier+','+OGDMES_property+'language,madatory field missing,""')
				reportError(OGDMES_fileIdentifier+','+OGDMES_property+'contentType,madatory field missing,""')

			json_record['resources'].append(json_record_resource)

		json_records.append(json_record)

		print "\nOGDMES\n"
		for key, value in sorted(debug_output.items()):
			print key + ':',
			if isinstance(value, unicode):
				value = value.encode('utf-8')
			print value

		continue

	if len(error_output) > 0:
		print "\nERRORS\n"
		sorted(error_output)
		for error in error_output:
			print error

	output = codecs.open(output_json, 'w', 'utf-8')
	utf_8_output = json.dumps(json_records, sort_keys=False, indent=4, separators=(',', ': '))
	output.write(utf_8_output)
	output.close()

	output = codecs.open(output_jl, 'w', 'utf-8')
	for json_record in json_records:
		utf_8_output = json.dumps(json_record, ensure_ascii=False, encoding='utf8')
		output.write(utf_8_output+"\n")
	output.close()

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

# Controled lists
GC_Registry_of_Applied_Terms = {
	'Aboriginal Affairs and Northern Development Canada'                              :[u'Aboriginal Affairs and Northern Development Canada',u'AANDC',u'Affaires autochtones et Développement du Nord Canada',u'AADNC',u'249'],
	'Agriculture and Agri-Food Canada'                                                :[u'Agriculture and Agri-Food Canada',u'AAFC',u'Agriculture et Agroalimentaire Canada',u'AAC',u'235'],
	'Atlantic Canada Opportunities Agency'                                            :[u'Atlantic Canada Opportunities Agency',u'ACOA',u'Agence de promotion économique du Canada atlantique',u'APECA',u'276'],
	'Atlantic Pilotage Authority Canada'                                              :[u'Atlantic Pilotage Authority Canada',u'APA',u'Administration de pilotage de l\'Atlantique Canada',u'APA',u'221'],
	'Atomic Energy of Canada Limited'                                                 :[u'Atomic Energy of Canada Limited',u'',u'Énergie atomique du Canada, Limitée',u'',u'138'],
	'Blue Water Bridge Canada'                                                        :[u'Blue Water Bridge Canada',u'BWBC',u'Pont Blue Water Canada',u'PBWC',u'103'],
	'Business Development Bank of Canada'                                             :[u'Business Development Bank of Canada',u'BDC',u'Banque de développement du Canada',u'BDC',u'150'],
	'Canada Border Services Agency'                                                   :[u'Canada Border Services Agency',u'CBSA',u'Agence des services frontaliers du Canada',u'ASFC',u'229'],
	'Canada Deposit Insurance Corporation'                                            :[u'Canada Deposit Insurance Corporation',u'CDIC',u'Société d\'assurance-dépôts du Canada',u'SADC',u'273'],
	'Canada Development Investment Corporation'                                       :[u'Canada Development Investment Corporation',u'CDEV',u'Corporation de développement des investissements du Canada',u'CDEV',u'148'],
	'Canada Emission Reduction Incentives Agency'                                     :[u'Canada Emission Reduction Incentives Agency',u'',u'Agence canadienne pour l\'incitation à la réduction des émissions',u'',u'277'],
	'Canada Employment Insurance Commission'                                          :[u'Canada Employment Insurance Commission',u'CEIC',u'Commission de l\'assurance-emploi du Canada',u'CAEC',u'196'],
	'Canada Employment Insurance Financing Board'                                     :[u'Canada Employment Insurance Financing Board',u'',u'Office de financement de l\'assurance-emploi du Canada',u'',u'176'],
	'Canada Industrial Relations Board'                                               :[u'Canada Industrial Relations Board',u'CIRB',u'Conseil canadien des relations industrielles',u'CCRI',u'188'],
	'Canada Lands Company Limited'                                                    :[u'Canada Lands Company Limited',u'',u'Société immobilière du Canada Limitée',u'',u'82'],
	'Canada Mortgage and Housing Corporation'                                         :[u'Canada Mortgage and Housing Corporation',u'CMHC',u'Société canadienne d\'hypothèques et de logement',u'SCHL',u'87'],
	'Canada Post'                                                                     :[u'Canada Post',u'CPC',u'Postes Canada',u'SCP',u'83'],
	'Canada Revenue Agency'                                                           :[u'Canada Revenue Agency',u'CRA',u'Agence du revenu du Canada',u'ARC',u'47'],
	'Canada School of Public Service'                                                 :[u'Canada School of Public Service',u'CSPS',u'École de la fonction publique du Canada',u'EFPC',u'73'],
	'Canada Science and Technology Museum'                                            :[u'Canada Science and Technology Museum',u'CSTM',u'Musée des sciences et de la technologie du Canada',u'MSTC',u'202'],
	'Canadian Air Transport Security Authority'                                       :[u'Canadian Air Transport Security Authority',u'CATSA',u'Administration canadienne de la sûreté du transport aérien',u'ACSTA',u'250'],
	'Canadian Artists and Producers Professional Relations Tribunal'                  :[u'Canadian Artists and Producers Professional Relations Tribunal',u'CAPPRT',u'Tribunal canadien des relations professionnelles artistes-producteurs',u'TCRPAP',u'24'],
	'Canadian Centre for Occupational Health and Safety'                              :[u'Canadian Centre for Occupational Health and Safety',u'CCOHS',u'Centre canadien d\'hygiène et de sécurité au travail',u'CCHST',u'35'],
	'Canadian Commercial Corporation'                                                 :[u'Canadian Commercial Corporation',u'CCC',u'Corporation commerciale canadienne',u'CCC',u'34'],
	'Canadian Dairy Commission'                                                       :[u'Canadian Dairy Commission',u'CDC',u'Commission canadienne du lait',u'CCL',u'151'],
	'Canadian Environmental Assessment Agency'                                        :[u'Canadian Environmental Assessment Agency',u'CEAA',u'Agence canadienne d\'évaluation environnementale',u'ACEE',u'270'],
	'Canadian Food Inspection Agency'                                                 :[u'Canadian Food Inspection Agency',u'CFIA',u'Agence canadienne d\'inspection des aliments',u'ACIA',u'206'],
	'Canadian Forces Grievance Board'                                                 :[u'Canadian Forces Grievance Board',u'CFGB',u'Comité des griefs des Forces canadiennes',u'CGFC',u'43'],
	'Canadian Grain Commission'                                                       :[u'Canadian Grain Commission',u'CGC',u'Commission canadienne des grains',u'CCG',u'169'],
	'Canadian Heritage'                                                               :[u'Canadian Heritage',u'PCH',u'Patrimoine canadien',u'PCH',u'16'],
	'Canadian Human Rights Commission'                                                :[u'Canadian Human Rights Commission',u'CHRC',u'Commission canadienne des droits de la personne',u'CCDP',u'113'],
	'Canadian Institutes of Health Research'                                          :[u'Canadian Institutes of Health Research',u'CIHR',u'Instituts de recherche en santé du Canada',u'IRSC',u'236'],
	'Canadian Intergovernmental Conference Secretariat'                               :[u'Canadian Intergovernmental Conference Secretariat',u'CICS',u'Secrétariat des conférences intergouvernementales canadiennes',u'SCIC',u'274'],
	'Canadian International Development Agency'                                       :[u'Canadian International Development Agency',u'CIDA',u'Agence canadienne de développement international',u'ACDI',u'218'],
	'Canadian International Trade Tribunal'                                           :[u'Canadian International Trade Tribunal',u'CITT',u'Tribunal canadien du commerce extérieur',u'TCCE',u'175'],
	'Canadian Museum for Human Rights'                                                :[u'Canadian Museum for Human Rights',u'CMHR',u'Musée canadien pour les droits de la personne',u'MCDP',u'267'],
	'Canadian Museum of Civilization'                                                 :[u'Canadian Museum of Civilization',u'CMC',u'Musée canadien des civilisations',u'MCC',u'263'],
	'Canadian Museum of Immigration at Pier 21'                                       :[u'Canadian Museum of Immigration at Pier 21',u'CMIP',u'Musée canadien de l\'immigration du Quai 21',u'MCIQ',u'2'],
	'Canadian Museum of Nature'                                                       :[u'Canadian Museum of Nature',u'CMN',u'Musée canadien de la nature',u'MCN',u'57'],
	'Canadian Northern Economic Development Agency'                                   :[u'Canadian Northern Economic Development Agency',u'CanNor',u'Agence canadienne de développement économique du Nord',u'CanNor',u'4'],
	'Canadian Nuclear Safety Commission'                                              :[u'Canadian Nuclear Safety Commission',u'CNSC',u'Commission canadienne de sûreté nucléaire',u'CCSN',u'58'],
	'Canadian Polar Commission'                                                       :[u'Canadian Polar Commission',u'POLAR',u'Commission canadienne des affaires polaires',u'POLAIRE',u'143'],
	'Canadian Radio-television and Telecommunications Commission'                     :[u'Canadian Radio-television and Telecommunications Commission',u'CRTC',u'Conseil de la radiodiffusion et des télécommunications canadiennes',u'CRTC',u'126'],
	'Canadian Security Intelligence Service'                                          :[u'Canadian Security Intelligence Service',u'CSIS',u'Service canadien du renseignement de sécurité',u'SCRS',u'90'],
	'Canadian Space Agency'                                                           :[u'Canadian Space Agency',u'CSA',u'Agence spatiale canadienne',u'ASC',u'3'],
	'Canadian Tourism Commission'                                                     :[u'Canadian Tourism Commission',u'',u'Commission canadienne du tourisme',u'',u'178'],
	'Canadian Transportation Agency'                                                  :[u'Canadian Transportation Agency',u'CTA',u'Office des transports du Canada',u'OTC',u'124'],
	'Citizenship and Immigration Canada'                                              :[u'Citizenship and Immigration Canada',u'CIC',u'Citoyenneté et Immigration Canada',u'CIC',u'94'],
	'Commission for Public Complaints Against the Royal Canadian Mounted Police'      :[u'Commission for Public Complaints Against the Royal Canadian Mounted Police',u'CPC',u'Commission des plaintes du public contre la Gendarmerie royale du Canada',u'CPP',u'136'],
	'Communications Security Establishment Canada'                                    :[u'Communications Security Establishment Canada',u'CSEC',u'Centre de la sécurité des télécommunications Canada',u'CSTC',u'156'],
	'Copyright Board Canada'                                                          :[u'Copyright Board Canada',u'CB',u'Commission du droit d\'auteur Canada',u'CDA',u'116'],
	'Corporation for the Mitigation of Mackenzie Gas Project Impacts'                 :[u'Corporation for the Mitigation of Mackenzie Gas Project Impacts',u'',u'Société d\'atténuation des répercussions du projet gazier Mackenzie',u'',u'1'],
	'Correctional Service of Canada'                                                  :[u'Correctional Service of Canada',u'CSC',u'Service correctionnel du Canada',u'SCC',u'193'],
	'Courts Administration Service'                                                   :[u'Courts Administration Service',u'CAS',u'Service administratif des tribunaux judiciaires',u'SATJ',u'228'],
	'Defence Construction Canada'                                                     :[u'Defence Construction Canada',u'DCC',u'Construction de Défense Canada',u'CDC',u'28'],
	'Department of Finance Canada'                                                    :[u'Department of Finance Canada',u'FIN',u'Ministère des Finances Canada',u'FIN',u'157'],
	'Department of Justice Canada'                                                    :[u'Department of Justice Canada',u'JUS',u'Ministère de la Justice Canada',u'JUS',u'119'],
	'Department of Social Development'                                                :[u'Department of Social Development',u'',u'Ministère du Développement social',u'',u'55556'],
	'Economic Development Agency of Canada for the Regions of Quebec'                 :[u'Economic Development Agency of Canada for the Regions of Quebec',u'CED',u'Agence de développement économique du Canada pour les régions du Québec',u'DEC',u'93'],
	'Elections Canada'                                                                :[u'Elections Canada',u'elections',u'Élections Canada ',u'elections',u'285'],
	'Enterprise Cape Breton Corporation'                                              :[u'Enterprise Cape Breton Corporation',u'',u'Société d\'expansion du Cap-Breton',u'',u'203'],
	'Environment Canada'                                                              :[u'Environment Canada',u'EC',u'Environnement Canada',u'EC',u'99'],
	'Export Development Canada'                                                       :[u'Export Development Canada',u'EDC',u'Exportation et développement Canada',u'EDC',u'62'],
	'Farm Credit Canada'                                                              :[u'Farm Credit Canada',u'FCC',u'Financement agricole Canada',u'FAC',u'23'],
	'Farm Products Council of Canada'                                                 :[u'Farm Products Council of Canada',u'FPCC',u'Conseil des produits agricoles du Canada',u'CPAC',u'200'],
	'Federal Bridge Corporation'                                                      :[u'Federal Bridge Corporation',u'FBCL',u'Société des ponts fédéraux',u'SPFL',u'254'],
	'Federal Economic Development Agency for Southern Ontario'                        :[u'Federal Economic Development Agency for Southern Ontario',u'FedDev Ontario',u'Agence fédérale de développement économique pour le Sud de l\'Ontario',u'FedDev Ontario',u'21'],
	'Financial Consumer Agency of Canada'                                             :[u'Financial Consumer Agency of Canada',u'FCAC',u'Agence de la consommation en matière financière du Canada',u'ACFC',u'224'],
	'Financial Transactions and Reports Analysis Centre of Canada'                    :[u'Financial Transactions and Reports Analysis Centre of Canada',u'FINTRAC',u'Centre d\'analyse des opérations et déclarations financières du Canada',u'CANAFE',u'127'],
	'First Nations Statistical Institute'                                             :[u'First Nations Statistical Institute',u'',u'Institut de la statistique des premières nations',u'',u'120'],
	'Fisheries and Oceans Canada'                                                     :[u'Fisheries and Oceans Canada',u'DFO',u'Pêches et Océans Canada',u'MPO',u'253'],
	'Foreign Affairs and International Trade Canada'                                  :[u'Foreign Affairs and International Trade Canada',u'DFAIT',u'Affaires étrangères et Commerce international Canada',u'MAECI',u'64'],
	'Freshwater Fish Marketing Corporation'                                           :[u'Freshwater Fish Marketing Corporation',u'FFMC',u'Office de commercialisation du poisson d\'eau douce',u'OCPED',u'252'],
	'Great Lakes Pilotage Authority Canada'                                           :[u'Great Lakes Pilotage Authority Canada',u'GLPA',u'Administration de pilotage des Grands Lacs Canada',u'APGL',u'261'],
	'Hazardous Materials Information Review Commission Canada'                        :[u'Hazardous Materials Information Review Commission Canada',u'HMIRC',u'Conseil de contrôle des renseignements relatifs aux matières dangereuses Canada',u'CCRMD',u'49'],
	'Health Canada'                                                                   :[u'Health Canada',u'HC',u'Santé Canada',u'SC',u'271'],
	'Human Resources and Skills Development Canada'                                   :[u'Human Resources and Skills Development Canada',u'HRSDC',u'Ressources humaines et Développement des compétences Canada',u'RHDCC',u'141'],
	'Human Rights Tribunal of Canada'                                                 :[u'Human Rights Tribunal of Canada',u'HRTC',u'Tribunal des droits de la personne du Canada',u'TDPC',u'164'],
	'Immigration and Refugee Board of Canada'                                         :[u'Immigration and Refugee Board of Canada',u'IRB',u'Commission de l\'immigration et du statut de réfugié du Canada',u'CISR',u'5'],
	'Indian Residential Schools Truth and Reconciliation Commission'                  :[u'Indian Residential Schools Truth and Reconciliation Commission',u'',u'Commission de vérité et de réconciliation relative aux pensionnats indiens',u'',u'245'],
	'Industry Canada'                                                                 :[u'Industry Canada',u'IC',u'Industrie Canada',u'IC',u'230'],
	'Infrastructure Canada'                                                           :[u'Infrastructure Canada',u'INFC',u'Infrastructure Canada',u'INFC',u'278'],
	'Laurentian Pilotage Authority Canada'                                            :[u'Laurentian Pilotage Authority Canada',u'LPA',u'Administration de pilotage des Laurentides Canada',u'APL',u'213'],
	'Law Commission of Canada'                                                        :[u'Law Commission of Canada',u'',u'Commission du droit du Canada',u'',u'231'],
	'Library and Archives Canada'                                                     :[u'Library and Archives Canada',u'LAC',u'Bibliothèque et Archives Canada',u'BAC',u'129'],
	'Library of Parliament'                                                           :[u'Library of Parliament',u'LP',u'Bibliothèque du Parlement ',u'BP',u'55555'],
	'Marine Atlantic Inc.'                                                            :[u'Marine Atlantic Inc.',u'',u'Marine Atlantique S.C.C.',u'',u'238'],
	'Military Police Complaints Commission of Canada'                                 :[u'Military Police Complaints Commission of Canada',u'MPCC',u'Commission d\'examen des plaintes concernant la police militaire du Canada',u'CPPM',u'66'],
	'National Capital Commission'                                                     :[u'National Capital Commission',u'NCC',u'Commission de la capitale nationale',u'CCN',u'22'],
	'National Defence'                                                                :[u'National Defence',u'DND',u'Défense nationale',u'MDN',u'32'],
	'National Energy Board'                                                           :[u'National Energy Board',u'NEB',u'Office national de l\'énergie',u'ONE',u'239'],
	'National Film Board'                                                             :[u'National Film Board',u'NFB',u'Office national du film',u'ONF',u'167'],
	'National Gallery of Canada'                                                      :[u'National Gallery of Canada',u'NGC',u'Musée des beaux-arts du Canada',u'MBAC',u'59'],
	'National Research Council Canada'                                                :[u'National Research Council Canada',u'NRC',u'Conseil national de recherches Canada',u'CNRC',u'172'],
	'National Round Table on the Environment and the Economy'                         :[u'National Round Table on the Environment and the Economy',u'',u'Table ronde nationale sur l\'environnement et l\'économie',u'',u'100'],
	'Natural Resources Canada'                                                        :[u'Natural Resources Canada',u'NRCan',u'Ressources naturelles Canada',u'RNCan',u'115'],
	'Northern Pipeline Agency Canada'                                                 :[u'Northern Pipeline Agency Canada',u'NPA',u'Administration du pipe-line du Nord Canada',u'APN',u'10'],
	'Office of the Auditor General of Canada'                                         :[u'Office of the Auditor General of Canada',u'OAG',u'Bureau du vérificateur général du Canada',u'BVG',u'125'],
	'Office of the Commissioner for Federal Judicial Affairs Canada'                  :[u'Office of the Commissioner for Federal Judicial Affairs Canada',u'FJA',u'Commissariat à la magistrature fédérale Canada',u'CMF',u'140'],
	'Office of the Commissioner of Lobbying of Canada'                                :[u'Office of the Commissioner of Lobbying of Canada',u'OCL',u'Commissariat au lobbying du Canada',u'CAL',u'205'],
	'Office of the Commissioner of Official Languages'                                :[u'Office of the Commissioner of Official Languages',u'OCOL',u'Commissariat aux langues officielles',u'CLO',u'258'],
	'Office of the Communications Security Establishment Commissioner'                :[u'Office of the Communications Security Establishment Commissioner',u'OCSEC',u'Bureau du commissaire du Centre de la sécurité des télécommunications',u'BCCST',u'279'],
	'Office of the Public Sector Integrity Commissioner of Canada'                    :[u'Office of the Public Sector Integrity Commissioner of Canada',u'PSIC',u'Commissariat à l\'intégrité du secteur public du Canada',u'ISPC',u'210'],
	'Office of the Secretary to the Governor General'                                 :[u'Office of the Secretary to the Governor General',u'OSGG',u'Bureau du secrétaire du gouverneur général',u'BSGG',u'5557'],
	'Office of the Superintendent of Financial Institutions Canada'                   :[u'Office of the Superintendent of Financial Institutions Canada',u'OSFI',u'Bureau du surintendant des institutions financières Canada',u'BSIF',u'184'],
	'Offices of the Information and Privacy Commissioners of Canada'                  :[u'Offices of the Information and Privacy Commissioners of Canada',u'OIC',u'Commissariats à l’information et à la protection de la vie privée au Canada',u'CI',u'41'],
	'Offices of the Information and Privacy Commissioners of Canada'                  :[u'Offices of the Information and Privacy Commissioners of Canada',u'OPC',u'Commissariats à l’information et à la protection de la vie privée au Canada',u'CPVP',u'226'],
	'Pacific Pilotage Authority Canada'                                               :[u'Pacific Pilotage Authority Canada',u'PPA',u'Administration de pilotage du Pacifique Canada',u'APP',u'165'],
	'Parks Canada'                                                                    :[u'Parks Canada',u'PC',u'Parcs Canada',u'PC',u'154'],
	'Parole Board of Canada'                                                          :[u'Parole Board of Canada',u'PBC',u'Commission des libérations conditionnelles du Canada',u'CLCC',u'246'],
	'Patented Medicine Prices Review Board Canada'                                    :[u'Patented Medicine Prices Review Board Canada',u'',u'Conseil d\'examen du prix des médicaments brevetés Canada',u'',u'15'],
	'Privy Council Office'                                                            :[u'Privy Council Office',u'',u'Bureau du Conseil privé',u'',u'173'],
	'Public Health Agency of Canada'                                                  :[u'Public Health Agency of Canada',u'PHAC',u'Agence de la santé publique du Canada',u'ASPC',u'135'],
	'Public Prosecution Service of Canada'                                            :[u'Public Prosecution Service of Canada',u'PPSC',u'Service des poursuites pénales du Canada',u'SPPC',u'98'],
	'Public Safety Canada'                                                            :[u'Public Safety Canada',u'PS',u'Sécurité publique Canada',u'SP',u'214'],
	'Public Servants Disclosure Protection Tribunal Canada'                           :[u'Public Servants Disclosure Protection Tribunal Canada',u'PSDPTC',u'Tribunal de la protection des fonctionnaires divulgateurs Canada',u'TPFDC',u'40'],
	'Public Service Commission of Canada'                                             :[u'Public Service Commission of Canada',u'PSC',u'Commission de la fonction publique du Canada',u'CFP',u'227'],
	'Public Service Labour Relations Board'                                           :[u'Public Service Labour Relations Board',u'PSLRB',u'Commission des relations de travail dans la fonction publique',u'CRTFP',u'102'],
	'Public Service Staffing Tribunal'                                                :[u'Public Service Staffing Tribunal',u'PSST',u'Tribunal de la dotation de la fonction publique',u'TDFP',u'266'],
	'Public Works and Government Services Canada'                                     :[u'Public Works and Government Services Canada',u'PWGSC',u'Travaux publics et Services gouvernementaux Canada',u'TPSGC',u'81'],
	'RCMP External Review Committee'                                                  :[u'RCMP External Review Committee',u'ERC',u'Comité externe d\'examen de la GRC',u'CEE',u'232'],
	'Registrar of the Supreme Court of Canada and that portion of the federal public administration appointed under subsection 12(2) of the Supreme Court Act'                 :[u'Registrar of the Supreme Court of Canada and that portion of the federal public administration appointed under subsection 12(2) of the Supreme Court Act',u'SCC',u'Registraire de la Cour suprême du Canada et le secteur de l\'administration publique fédérale nommé en vertu du paragraphe 12(2) de la Loi sur la Cour suprême',u'CSC',u'63'],
	'Registry of the Competition Tribunal'                                            :[u'Registry of the Competition Tribunal',u'RCT',u'Greffe du Tribunal de la concurrence',u'GTC',u'89'],
	'Registry of the Specific Claims Tribunal of Canada'                              :[u'Registry of the Specific Claims Tribunal of Canada',u'SCT',u'Greffe du Tribunal des revendications particulières du Canada',u'TRP',u'220'],
	'Ridley Terminals Inc.'                                                           :[u'Ridley Terminals Inc.',u'',u'Ridley Terminals Inc.',u'',u'142'],
	'Royal Canadian Mint'                                                             :[u'Royal Canadian Mint',u'',u'Monnaie royale canadienne',u'',u'18'],
	'Royal Canadian Mounted Police'                                                   :[u'Royal Canadian Mounted Police',u'RCMP',u'Gendarmerie royale du Canada',u'GRC',u'131'],
	'Science and Engineering Research Canada'                                         :[u'Science and Engineering Research Canada',u'SERC',u'Recherches en sciences et en génie Canada',u'RSGC',u'110'],
	'Security Intelligence Review Committee'                                          :[u'Security Intelligence Review Committee',u'SIRC',u'Comité de surveillance des activités de renseignement de sécurité',u'CSARS',u'109'],
	'Shared Services Canada'                                                          :[u'Shared Services Canada',u'SSC',u'Services partagés Canada',u'SPC',u'92'],
	'Social Sciences and Humanities Research Council of Canada'                       :[u'Social Sciences and Humanities Research Council of Canada',u'SSHRC',u'Conseil de recherches en sciences humaines du Canada',u'CRSH',u'207'],
	'Standards Council of Canada'                                                     :[u'Standards Council of Canada',u'SCC-CCN',u'Conseil canadien des normes',u'SCC-CCN',u'107'],
	'Statistics Canada'                                                               :[u'Statistics Canada',u'StatCan',u'Statistique Canada',u'StatCan',u'256'],
	'Status of Women Canada'                                                          :[u'Status of Women Canada',u'SWC',u'Condition féminine Canada',u'CFC',u'147'],
	'The Correctional Investigator Canada'                                            :[u'The Correctional Investigator Canada',u'OCI',u'L\'Enquêteur correctionnel Canada',u'BEC',u'5555'],
	'The National Battlefields Commission'                                            :[u'The National Battlefields Commission',u'NBC',u'Commission des champs de bataille nationaux',u'CCBN',u'262'],
	'Transport Canada'                                                                :[u'Transport Canada',u'TC',u'Transports Canada',u'TC',u'217'],
	'Transportation Appeal Tribunal of Canada'                                        :[u'Transportation Appeal Tribunal of Canada',u'TATC',u'Tribunal d\'appel des transports du Canada',u'TATC',u'96'],
	'Transportation Safety Board of Canada'                                           :[u'Transportation Safety Board of Canada',u'TSB',u'Bureau de la sécurité des transports du Canada',u'BST',u'215'],
	'Treasury Board'                                                                  :[u'Treasury Board',u'TB',u'Conseil du Trésor',u'CT',u'105'],
	'Treasury Board of Canada Secretariat'                                            :[u'Treasury Board of Canada Secretariat',u'TBS',u'Secrétariat du Conseil du Trésor du Canada',u'SCT',u'139'],
	'Veterans Affairs Canada'                                                         :[u'Veterans Affairs Canada',u'VAC',u'Anciens Combattants Canada',u'ACC',u'189'],
	'Veterans Review and Appeal Board'                                                :[u'Veterans Review and Appeal Board',u'VRAB',u'Tribunal des anciens combattants (révision et appel)',u'TACRA',u'85'],
	'VIA Rail Canada Inc.'                                                            :[u'VIA Rail Canada Inc.',u'',u'VIA Rail Canada Inc.',u'',u'55555'],
	'Western Economic Diversification Canada'                                         :[u'Western Economic Diversification Canada',u'WD',u'Diversification de l\'économie de l\'Ouest Canada',u'DEO',u'55'],
	'Windsor-Detroit Bridge Authority'                                                :[u'Windsor-Detroit Bridge Authority',u'',u'Autorité du pont Windsor-Détroit',u'',u'55553'],
	'Affaires autochtones et Développement du Nord Canada'                            :[u'Aboriginal Affairs and Northern Development Canada',u'AANDC',u'Affaires autochtones et Développement du Nord Canada',u'AADNC',u'249'],
	'Agriculture et Agroalimentaire Canada'                                           :[u'Agriculture and Agri-Food Canada',u'AAFC',u'Agriculture et Agroalimentaire Canada',u'AAC',u'235'],
	'Agence de promotion économique du Canada atlantique'                             :[u'Atlantic Canada Opportunities Agency',u'ACOA',u'Agence de promotion économique du Canada atlantique',u'APECA',u'276'],
	'Administration de pilotage de l\'Atlantique Canada'                              :[u'Atlantic Pilotage Authority Canada',u'APA',u'Administration de pilotage de l\'Atlantique Canada',u'APA',u'221'],
	'Énergie atomique du Canada, Limitée'                                             :[u'Atomic Energy of Canada Limited',u'',u'Énergie atomique du Canada, Limitée',u'',u'138'],
	'Pont Blue Water Canada'                                                          :[u'Blue Water Bridge Canada',u'BWBC',u'Pont Blue Water Canada',u'PBWC',u'103'],
	'Banque de développement du Canada'                                               :[u'Business Development Bank of Canada',u'BDC',u'Banque de développement du Canada',u'BDC',u'150'],
	'Agence des services frontaliers du Canada'                                       :[u'Canada Border Services Agency',u'CBSA',u'Agence des services frontaliers du Canada',u'ASFC',u'229'],
	'Société d\'assurance-dépôts du Canada'                                           :[u'Canada Deposit Insurance Corporation',u'CDIC',u'Société d\'assurance-dépôts du Canada',u'SADC',u'273'],
	'Corporation de développement des investissements du Canada'                      :[u'Canada Development Investment Corporation',u'CDEV',u'Corporation de développement des investissements du Canada',u'CDEV',u'148'],
	'Agence canadienne pour l\'incitation à la réduction des émissions'               :[u'Canada Emission Reduction Incentives Agency',u'',u'Agence canadienne pour l\'incitation à la réduction des émissions',u'',u'277'],
	'Commission de l\'assurance-emploi du Canada'                                     :[u'Canada Employment Insurance Commission',u'CEIC',u'Commission de l\'assurance-emploi du Canada',u'CAEC',u'196'],
	'Office de financement de l\'assurance-emploi du Canada'                          :[u'Canada Employment Insurance Financing Board',u'',u'Office de financement de l\'assurance-emploi du Canada',u'',u'176'],
	'Conseil canadien des relations industrielles'                                    :[u'Canada Industrial Relations Board',u'CIRB',u'Conseil canadien des relations industrielles',u'CCRI',u'188'],
	'Société immobilière du Canada Limitée'                                           :[u'Canada Lands Company Limited',u'',u'Société immobilière du Canada Limitée',u'',u'82'],
	'Société canadienne d\'hypothèques et de logement'                                :[u'Canada Mortgage and Housing Corporation',u'CMHC',u'Société canadienne d\'hypothèques et de logement',u'SCHL',u'87'],
	'Postes Canada'                                                                   :[u'Canada Post',u'CPC',u'Postes Canada',u'SCP',u'83'],
	'Agence du revenu du Canada'                                                      :[u'Canada Revenue Agency',u'CRA',u'Agence du revenu du Canada',u'ARC',u'47'],
	'École de la fonction publique du Canada'                                         :[u'Canada School of Public Service',u'CSPS',u'École de la fonction publique du Canada',u'EFPC',u'73'],
	'Musée des sciences et de la technologie du Canada'                               :[u'Canada Science and Technology Museum',u'CSTM',u'Musée des sciences et de la technologie du Canada',u'MSTC',u'202'],
	'Administration canadienne de la sûreté du transport aérien'                      :[u'Canadian Air Transport Security Authority',u'CATSA',u'Administration canadienne de la sûreté du transport aérien',u'ACSTA',u'250'],
	'Tribunal canadien des relations professionnelles artistes-producteurs'           :[u'Canadian Artists and Producers Professional Relations Tribunal',u'CAPPRT',u'Tribunal canadien des relations professionnelles artistes-producteurs',u'TCRPAP',u'24'],
	'Centre canadien d\'hygiène et de sécurité au travail'                            :[u'Canadian Centre for Occupational Health and Safety',u'CCOHS',u'Centre canadien d\'hygiène et de sécurité au travail',u'CCHST',u'35'],
	'Corporation commerciale canadienne'                                              :[u'Canadian Commercial Corporation',u'CCC',u'Corporation commerciale canadienne',u'CCC',u'34'],
	'Commission canadienne du lait'                                                   :[u'Canadian Dairy Commission',u'CDC',u'Commission canadienne du lait',u'CCL',u'151'],
	'Agence canadienne d\'évaluation environnementale'                                :[u'Canadian Environmental Assessment Agency',u'CEAA',u'Agence canadienne d\'évaluation environnementale',u'ACEE',u'270'],
	'Agence canadienne d\'inspection des aliments'                                    :[u'Canadian Food Inspection Agency',u'CFIA',u'Agence canadienne d\'inspection des aliments',u'ACIA',u'206'],
	'Comité des griefs des Forces canadiennes'                                        :[u'Canadian Forces Grievance Board',u'CFGB',u'Comité des griefs des Forces canadiennes',u'CGFC',u'43'],
	'Commission canadienne des grains'                                                :[u'Canadian Grain Commission',u'CGC',u'Commission canadienne des grains',u'CCG',u'169'],
	'Patrimoine canadien'                                                             :[u'Canadian Heritage',u'PCH',u'Patrimoine canadien',u'PCH',u'16'],
	'Commission canadienne des droits de la personne'                                 :[u'Canadian Human Rights Commission',u'CHRC',u'Commission canadienne des droits de la personne',u'CCDP',u'113'],
	'Instituts de recherche en santé du Canada'                                       :[u'Canadian Institutes of Health Research',u'CIHR',u'Instituts de recherche en santé du Canada',u'IRSC',u'236'],
	'Secrétariat des conférences intergouvernementales canadiennes'                   :[u'Canadian Intergovernmental Conference Secretariat',u'CICS',u'Secrétariat des conférences intergouvernementales canadiennes',u'SCIC',u'274'],
	'Agence canadienne de développement international'                                :[u'Canadian International Development Agency',u'CIDA',u'Agence canadienne de développement international',u'ACDI',u'218'],
	'Tribunal canadien du commerce extérieur'                                         :[u'Canadian International Trade Tribunal',u'CITT',u'Tribunal canadien du commerce extérieur',u'TCCE',u'175'],
	'Musée canadien pour les droits de la personne'                                   :[u'Canadian Museum for Human Rights',u'CMHR',u'Musée canadien pour les droits de la personne',u'MCDP',u'267'],
	'Musée canadien des civilisations'                                                :[u'Canadian Museum of Civilization',u'CMC',u'Musée canadien des civilisations',u'MCC',u'263'],
	'Musée canadien de l\'immigration du Quai 21'                                     :[u'Canadian Museum of Immigration at Pier 21',u'CMIP',u'Musée canadien de l\'immigration du Quai 21',u'MCIQ',u'2'],
	'Musée canadien de la nature'                                                     :[u'Canadian Museum of Nature',u'CMN',u'Musée canadien de la nature',u'MCN',u'57'],
	'Agence canadienne de développement économique du Nord'                           :[u'Canadian Northern Economic Development Agency',u'CanNor',u'Agence canadienne de développement économique du Nord',u'CanNor',u'4'],
	'Commission canadienne de sûreté nucléaire'                                       :[u'Canadian Nuclear Safety Commission',u'CNSC',u'Commission canadienne de sûreté nucléaire',u'CCSN',u'58'],
	'Commission canadienne des affaires polaires'                                     :[u'Canadian Polar Commission',u'POLAR',u'Commission canadienne des affaires polaires',u'POLAIRE',u'143'],
	'Conseil de la radiodiffusion et des télécommunications canadiennes'              :[u'Canadian Radio-television and Telecommunications Commission',u'CRTC',u'Conseil de la radiodiffusion et des télécommunications canadiennes',u'CRTC',u'126'],
	'Service canadien du renseignement de sécurité'                                   :[u'Canadian Security Intelligence Service',u'CSIS',u'Service canadien du renseignement de sécurité',u'SCRS',u'90'],
	'Agence spatiale canadienne'                                                      :[u'Canadian Space Agency',u'CSA',u'Agence spatiale canadienne',u'ASC',u'3'],
	'Commission canadienne du tourisme'                                               :[u'Canadian Tourism Commission',u'',u'Commission canadienne du tourisme',u'',u'178'],
	'Office des transports du Canada'                                                 :[u'Canadian Transportation Agency',u'CTA',u'Office des transports du Canada',u'OTC',u'124'],
	'Citoyenneté et Immigration Canada'                                               :[u'Citizenship and Immigration Canada',u'CIC',u'Citoyenneté et Immigration Canada',u'CIC',u'94'],
	'Commission des plaintes du public contre la Gendarmerie royale du Canada'        :[u'Commission for Public Complaints Against the Royal Canadian Mounted Police',u'CPC',u'Commission des plaintes du public contre la Gendarmerie royale du Canada',u'CPP',u'136'],
	'Centre de la sécurité des télécommunications Canada'                             :[u'Communications Security Establishment Canada',u'CSEC',u'Centre de la sécurité des télécommunications Canada',u'CSTC',u'156'],
	'Commission du droit d\'auteur Canada'                                            :[u'Copyright Board Canada',u'CB',u'Commission du droit d\'auteur Canada',u'CDA',u'116'],
	'Société d\'atténuation des répercussions du projet gazier Mackenzie'             :[u'Corporation for the Mitigation of Mackenzie Gas Project Impacts',u'',u'Société d\'atténuation des répercussions du projet gazier Mackenzie',u'',u'1'],
	'Service correctionnel du Canada'                                                 :[u'Correctional Service of Canada',u'CSC',u'Service correctionnel du Canada',u'SCC',u'193'],
	'Service administratif des tribunaux judiciaires'                                 :[u'Courts Administration Service',u'CAS',u'Service administratif des tribunaux judiciaires',u'SATJ',u'228'],
	'Construction de Défense Canada'                                                  :[u'Defence Construction Canada',u'DCC',u'Construction de Défense Canada',u'CDC',u'28'],
	'Ministère des Finances Canada'                                                   :[u'Department of Finance Canada',u'FIN',u'Ministère des Finances Canada',u'FIN',u'157'],
	'Ministère de la Justice Canada'                                                  :[u'Department of Justice Canada',u'JUS',u'Ministère de la Justice Canada',u'JUS',u'119'],
	'Ministère du Développement social'                                               :[u'Department of Social Development',u'',u'Ministère du Développement social',u'',u'55556'],
	'Agence de développement économique du Canada pour les régions du Québec'         :[u'Economic Development Agency of Canada for the Regions of Quebec',u'CED',u'Agence de développement économique du Canada pour les régions du Québec',u'DEC',u'93'],
	'Élections Canada '                                                               :[u'Elections Canada',u'elections',u'Élections Canada ',u'elections',u'285'],
	'Société d\'expansion du Cap-Breton'                                              :[u'Enterprise Cape Breton Corporation',u'',u'Société d\'expansion du Cap-Breton',u'',u'203'],
	'Environnement Canada'                                                            :[u'Environment Canada',u'EC',u'Environnement Canada',u'EC',u'99'],
	'Exportation et développement Canada'                                             :[u'Export Development Canada',u'EDC',u'Exportation et développement Canada',u'EDC',u'62'],
	'Financement agricole Canada'                                                     :[u'Farm Credit Canada',u'FCC',u'Financement agricole Canada',u'FAC',u'23'],
	'Conseil des produits agricoles du Canada'                                        :[u'Farm Products Council of Canada',u'FPCC',u'Conseil des produits agricoles du Canada',u'CPAC',u'200'],
	'Société des ponts fédéraux'                                                      :[u'Federal Bridge Corporation',u'FBCL',u'Société des ponts fédéraux',u'SPFL',u'254'],
	'Agence fédérale de développement économique pour le Sud de l\'Ontario'           :[u'Federal Economic Development Agency for Southern Ontario',u'FedDev Ontario',u'Agence fédérale de développement économique pour le Sud de l\'Ontario',u'FedDev Ontario',u'21'],
	'Agence de la consommation en matière financière du Canada'                       :[u'Financial Consumer Agency of Canada',u'FCAC',u'Agence de la consommation en matière financière du Canada',u'ACFC',u'224'],
	'Centre d\'analyse des opérations et déclarations financières du Canada'          :[u'Financial Transactions and Reports Analysis Centre of Canada',u'FINTRAC',u'Centre d\'analyse des opérations et déclarations financières du Canada',u'CANAFE',u'127'],
	'Institut de la statistique des premières nations'                                :[u'First Nations Statistical Institute',u'',u'Institut de la statistique des premières nations',u'',u'120'],
	'Pêches et Océans Canada'                                                         :[u'Fisheries and Oceans Canada',u'DFO',u'Pêches et Océans Canada',u'MPO',u'253'],
	'Affaires étrangères et Commerce international Canada'                            :[u'Foreign Affairs and International Trade Canada',u'DFAIT',u'Affaires étrangères et Commerce international Canada',u'MAECI',u'64'],
	'Office de commercialisation du poisson d\'eau douce'                             :[u'Freshwater Fish Marketing Corporation',u'FFMC',u'Office de commercialisation du poisson d\'eau douce',u'OCPED',u'252'],
	'Administration de pilotage des Grands Lacs Canada'                               :[u'Great Lakes Pilotage Authority Canada',u'GLPA',u'Administration de pilotage des Grands Lacs Canada',u'APGL',u'261'],
	'Conseil de contrôle des renseignements relatifs aux matières dangereuses Canada' :[u'Hazardous Materials Information Review Commission Canada',u'HMIRC',u'Conseil de contrôle des renseignements relatifs aux matières dangereuses Canada',u'CCRMD',u'49'],
	'Santé Canada'                                                                    :[u'Health Canada',u'HC',u'Santé Canada',u'SC',u'271'],
	'Ressources humaines et Développement des compétences Canada'                     :[u'Human Resources and Skills Development Canada',u'HRSDC',u'Ressources humaines et Développement des compétences Canada',u'RHDCC',u'141'],
	'Tribunal des droits de la personne du Canada'                                    :[u'Human Rights Tribunal of Canada',u'HRTC',u'Tribunal des droits de la personne du Canada',u'TDPC',u'164'],
	'Commission de l\'immigration et du statut de réfugié du Canada'                  :[u'Immigration and Refugee Board of Canada',u'IRB',u'Commission de l\'immigration et du statut de réfugié du Canada',u'CISR',u'5'],
	'Commission de vérité et de réconciliation relative aux pensionnats indiens'      :[u'Indian Residential Schools Truth and Reconciliation Commission',u'',u'Commission de vérité et de réconciliation relative aux pensionnats indiens',u'',u'245'],
	'Industrie Canada'                                                                :[u'Industry Canada',u'IC',u'Industrie Canada',u'IC',u'230'],
	'Infrastructure Canada'                                                           :[u'Infrastructure Canada',u'INFC',u'Infrastructure Canada',u'INFC',u'278'],
	'Administration de pilotage des Laurentides Canada'                               :[u'Laurentian Pilotage Authority Canada',u'LPA',u'Administration de pilotage des Laurentides Canada',u'APL',u'213'],
	'Commission du droit du Canada'                                                   :[u'Law Commission of Canada',u'',u'Commission du droit du Canada',u'',u'231'],
	'Bibliothèque et Archives Canada'                                                 :[u'Library and Archives Canada',u'LAC',u'Bibliothèque et Archives Canada',u'BAC',u'129'],
	'Bibliothèque du Parlement '                                                      :[u'Library of Parliament',u'LP',u'Bibliothèque du Parlement ',u'BP',u'55555'],
	'Marine Atlantique S.C.C.'                                                        :[u'Marine Atlantic Inc.',u'',u'Marine Atlantique S.C.C.',u'',u'238'],
	'Commission d\'examen des plaintes concernant la police militaire du Canada'      :[u'Military Police Complaints Commission of Canada',u'MPCC',u'Commission d\'examen des plaintes concernant la police militaire du Canada',u'CPPM',u'66'],
	'Commission de la capitale nationale'                                             :[u'National Capital Commission',u'NCC',u'Commission de la capitale nationale',u'CCN',u'22'],
	'Défense nationale'                                                               :[u'National Defence',u'DND',u'Défense nationale',u'MDN',u'32'],
	'Office national de l\'énergie'                                                   :[u'National Energy Board',u'NEB',u'Office national de l\'énergie',u'ONE',u'239'],
	'Office national du film'                                                         :[u'National Film Board',u'NFB',u'Office national du film',u'ONF',u'167'],
	'Musée des beaux-arts du Canada'                                                  :[u'National Gallery of Canada',u'NGC',u'Musée des beaux-arts du Canada',u'MBAC',u'59'],
	'Conseil national de recherches Canada'                                           :[u'National Research Council Canada',u'NRC',u'Conseil national de recherches Canada',u'CNRC',u'172'],
	'Table ronde nationale sur l\'environnement et l\'économie'                       :[u'National Round Table on the Environment and the Economy',u'',u'Table ronde nationale sur l\'environnement et l\'économie',u'',u'100'],
	'Ressources naturelles Canada'                                                    :[u'Natural Resources Canada',u'NRCan',u'Ressources naturelles Canada',u'RNCan',u'115'],
	'Administration du pipe-line du Nord Canada'                                      :[u'Northern Pipeline Agency Canada',u'NPA',u'Administration du pipe-line du Nord Canada',u'APN',u'10'],
	'Bureau du vérificateur général du Canada'                                        :[u'Office of the Auditor General of Canada',u'OAG',u'Bureau du vérificateur général du Canada',u'BVG',u'125'],
	'Commissariat à la magistrature fédérale Canada'                                  :[u'Office of the Commissioner for Federal Judicial Affairs Canada',u'FJA',u'Commissariat à la magistrature fédérale Canada',u'CMF',u'140'],
	'Commissariat au lobbying du Canada'                                              :[u'Office of the Commissioner of Lobbying of Canada',u'OCL',u'Commissariat au lobbying du Canada',u'CAL',u'205'],
	'Commissariat aux langues officielles'                                            :[u'Office of the Commissioner of Official Languages',u'OCOL',u'Commissariat aux langues officielles',u'CLO',u'258'],
	'Bureau du commissaire du Centre de la sécurité des télécommunications'           :[u'Office of the Communications Security Establishment Commissioner',u'OCSEC',u'Bureau du commissaire du Centre de la sécurité des télécommunications',u'BCCST',u'279'],
	'Commissariat à l\'intégrité du secteur public du Canada'                         :[u'Office of the Public Sector Integrity Commissioner of Canada',u'PSIC',u'Commissariat à l\'intégrité du secteur public du Canada',u'ISPC',u'210'],
	'Bureau du secrétaire du gouverneur général'                                      :[u'Office of the Secretary to the Governor General',u'OSGG',u'Bureau du secrétaire du gouverneur général',u'BSGG',u'5557'],
	'Bureau du surintendant des institutions financières Canada'                      :[u'Office of the Superintendent of Financial Institutions Canada',u'OSFI',u'Bureau du surintendant des institutions financières Canada',u'BSIF',u'184'],
	'Commissariats à l’information et à la protection de la vie privée au Canada'     :[u'Offices of the Information and Privacy Commissioners of Canada',u'OIC',u'Commissariats à l’information et à la protection de la vie privée au Canada',u'CI',u'41'],
	'Commissariats à l’information et à la protection de la vie privée au Canada'     :[u'Offices of the Information and Privacy Commissioners of Canada',u'OPC',u'Commissariats à l’information et à la protection de la vie privée au Canada',u'CPVP',u'226'],
	'Administration de pilotage du Pacifique Canada'                                  :[u'Pacific Pilotage Authority Canada',u'PPA',u'Administration de pilotage du Pacifique Canada',u'APP',u'165'],
	'Parcs Canada'                                                                    :[u'Parks Canada',u'PC',u'Parcs Canada',u'PC',u'154'],
	'Commission des libérations conditionnelles du Canada'                            :[u'Parole Board of Canada',u'PBC',u'Commission des libérations conditionnelles du Canada',u'CLCC',u'246'],
	'Conseil d\'examen du prix des médicaments brevetés Canada'                       :[u'Patented Medicine Prices Review Board Canada',u'',u'Conseil d\'examen du prix des médicaments brevetés Canada',u'',u'15'],
	'Bureau du Conseil privé'                                                         :[u'Privy Council Office',u'',u'Bureau du Conseil privé',u'',u'173'],
	'Agence de la santé publique du Canada'                                           :[u'Public Health Agency of Canada',u'PHAC',u'Agence de la santé publique du Canada',u'ASPC',u'135'],
	'Service des poursuites pénales du Canada'                                        :[u'Public Prosecution Service of Canada',u'PPSC',u'Service des poursuites pénales du Canada',u'SPPC',u'98'],
	'Sécurité publique Canada'                                                        :[u'Public Safety Canada',u'PS',u'Sécurité publique Canada',u'SP',u'214'],
	'Tribunal de la protection des fonctionnaires divulgateurs Canada'                :[u'Public Servants Disclosure Protection Tribunal Canada',u'PSDPTC',u'Tribunal de la protection des fonctionnaires divulgateurs Canada',u'TPFDC',u'40'],
	'Commission de la fonction publique du Canada'                                    :[u'Public Service Commission of Canada',u'PSC',u'Commission de la fonction publique du Canada',u'CFP',u'227'],
	'Commission des relations de travail dans la fonction publique'                   :[u'Public Service Labour Relations Board',u'PSLRB',u'Commission des relations de travail dans la fonction publique',u'CRTFP',u'102'],
	'Tribunal de la dotation de la fonction publique'                                 :[u'Public Service Staffing Tribunal',u'PSST',u'Tribunal de la dotation de la fonction publique',u'TDFP',u'266'],
	'Travaux publics et Services gouvernementaux Canada'                              :[u'Public Works and Government Services Canada',u'PWGSC',u'Travaux publics et Services gouvernementaux Canada',u'TPSGC',u'81'],
	'Comité externe d\'examen de la GRC'                                              :[u'RCMP External Review Committee',u'ERC',u'Comité externe d\'examen de la GRC',u'CEE',u'232'],
	'Registraire de la Cour suprême du Canada et le secteur de l\'administration publique fédérale nommé en vertu du paragraphe 12(2) de la Loi sur la Cour suprême'    :[u'Registrar of the Supreme Court of Canada and that portion of the federal public administration appointed under subsection 12(2) of the Supreme Court Act',u'SCC',u'Registraire de la Cour suprême du Canada et le secteur de l\'administration publique fédérale nommé en vertu du paragraphe 12(2) de la Loi sur la Cour suprême',u'CSC',u'63'],
	'Greffe du Tribunal de la concurrence'                                            :[u'Registry of the Competition Tribunal',u'RCT',u'Greffe du Tribunal de la concurrence',u'GTC',u'89'],
	'Greffe du Tribunal des revendications particulières du Canada'                   :[u'Registry of the Specific Claims Tribunal of Canada',u'SCT',u'Greffe du Tribunal des revendications particulières du Canada',u'TRP',u'220'],
	'Ridley Terminals Inc.'                                                           :[u'Ridley Terminals Inc.',u'',u'Ridley Terminals Inc.',u'',u'142'],
	'Monnaie royale canadienne'                                                       :[u'Royal Canadian Mint',u'',u'Monnaie royale canadienne',u'',u'18'],
	'Gendarmerie royale du Canada'                                                    :[u'Royal Canadian Mounted Police',u'RCMP',u'Gendarmerie royale du Canada',u'GRC',u'131'],
	'Recherches en sciences et en génie Canada'                                       :[u'Science and Engineering Research Canada',u'SERC',u'Recherches en sciences et en génie Canada',u'RSGC',u'110'],
	'Comité de surveillance des activités de renseignement de sécurité'               :[u'Security Intelligence Review Committee',u'SIRC',u'Comité de surveillance des activités de renseignement de sécurité',u'CSARS',u'109'],
	'Services partagés Canada'                                                        :[u'Shared Services Canada',u'SSC',u'Services partagés Canada',u'SPC',u'92'],
	'Conseil de recherches en sciences humaines du Canada'                            :[u'Social Sciences and Humanities Research Council of Canada',u'SSHRC',u'Conseil de recherches en sciences humaines du Canada',u'CRSH',u'207'],
	'Conseil canadien des normes'                                                     :[u'Standards Council of Canada',u'SCC-CCN',u'Conseil canadien des normes',u'SCC-CCN',u'107'],
	'Statistique Canada'                                                              :[u'Statistics Canada',u'StatCan',u'Statistique Canada',u'StatCan',u'256'],
	'Condition féminine Canada'                                                       :[u'Status of Women Canada',u'SWC',u'Condition féminine Canada',u'CFC',u'147'],
	'L\'Enquêteur correctionnel Canada'                                               :[u'The Correctional Investigator Canada',u'OCI',u'L\'Enquêteur correctionnel Canada',u'BEC',u'5555'],
	'Commission des champs de bataille nationaux'                                     :[u'The National Battlefields Commission',u'NBC',u'Commission des champs de bataille nationaux',u'CCBN',u'262'],
	'Transports Canada'                                                               :[u'Transport Canada',u'TC',u'Transports Canada',u'TC',u'217'],
	'Tribunal d\'appel des transports du Canada'                                      :[u'Transportation Appeal Tribunal of Canada',u'TATC',u'Tribunal d\'appel des transports du Canada',u'TATC',u'96'],
	'Bureau de la sécurité des transports du Canada'                                  :[u'Transportation Safety Board of Canada',u'TSB',u'Bureau de la sécurité des transports du Canada',u'BST',u'215'],
	'Conseil du Trésor'                                                               :[u'Treasury Board',u'TB',u'Conseil du Trésor',u'CT',u'105'],
	'Secrétariat du Conseil du Trésor du Canada'                                      :[u'Treasury Board of Canada Secretariat',u'TBS',u'Secrétariat du Conseil du Trésor du Canada',u'SCT',u'139'],
	'Anciens Combattants Canada'                                                      :[u'Veterans Affairs Canada',u'VAC',u'Anciens Combattants Canada',u'ACC',u'189'],
	'Tribunal des anciens combattants (révision et appel)'                            :[u'Veterans Review and Appeal Board',u'VRAB',u'Tribunal des anciens combattants (révision et appel)',u'TACRA',u'85'],
	'VIA Rail Canada Inc.'                                                            :[u'VIA Rail Canada Inc.',u'',u'VIA Rail Canada Inc.',u'',u'55555'],
	'Diversification de l\'économie de l\'Ouest Canada'                               :[u'Western Economic Diversification Canada',u'WD',u'Diversification de l\'économie de l\'Ouest Canada',u'DEO',u'55'],
	'Autorité du pont Windsor-Détroit'                                                :[u'Windsor-Detroit Bridge Authority',u'',u'Autorité du pont Windsor-Détroit',u'',u'55553'],
}

napCI_RoleCode                  = {
	'resourceProvider'              :[u'resourceProvider',       u'fournisseurRessource'],
	'fournisseurRessource'          :[u'resourceProvider',       u'fournisseurRessource'],
	'custodian'                     :[u'custodian',              u'conservateur'],
	'conservateur'                  :[u'custodian',              u'conservateur'],
	'owner'                         :[u'owner',                  u'propriétaire'],
	'propriétaire'                  :[u'owner',                  u'propriétaire'],
	'user'                          :[u'user',                   u'utilisateur'],
	'utilisateur'                   :[u'user',                   u'utilisateur'],
	'distributor'                   :[u'distributor',            u'distributeur'],
	'distributeur'                  :[u'distributor',            u'distributeur'],
	'pointOfContact'                :[u'pointOfContact',         u'contact'],
	'contact'                       :[u'pointOfContact',         u'contact'],
	'principalInvestigator'         :[u'principalInvestigator',  u'chercheurPrincipal'],
	'chercheurPrincipal'            :[u'principalInvestigator',  u'chercheurPrincipal'],
	'processor'                     :[u'processor',              u'traiteur'],
	'traiteur'                      :[u'processor',              u'traiteur'],
	'publisher'                     :[u'publisher',              u'éditeur'],
	'éditeur'                       :[u'publisher',              u'éditeur'],
	'author'                        :[u'author',                 u'auteur'],
	'auteur'                        :[u'author',                 u'auteur'],
	'collaborator'                  :[u'collaborator',           u'collaborateur'],
	'collaborateur'                 :[u'collaborator',           u'collaborateur'],
	'editor'                        :[u'editor',                 u'réviseur'],
	'réviseur'                      :[u'editor',                 u'réviseur'],
	'mediator'                      :[u'mediator',               u'médiateur'],
	'médiateur'                     :[u'mediator',               u'médiateur'],
	'rightsHolder'                  :[u'rightsHolder',           u'détenteurDroits'],
	'détenteurDroits'               :[u'rightsHolder',           u'détenteurDroits']
}

napMD_ProgressCode = {
	'completed'         :[u'completed',u'complété'],
	'historicalArchive' :[u'historicalArchive',u'archiveHistorique'],
	'obsolete'          :[u'obsolete',u'périmé'],
	'onGoing'           :[u'onGoing',u'enContinue'],
	'planned'           :[u'planned',u'planifié'],
	'required'          :[u'required',u'requis'],
	'underDevelopment'  :[u'underDevelopment',u'enProduction'],
	'proposed'          :[u'proposed',u'proposé'],
	'complété'          :[u'completed',u'complété'],
	'archiveHistorique' :[u'historicalArchive',u'archiveHistorique'],
	'périmé'            :[u'obsolete',u'périmé'],
	'enContinue'        :[u'onGoing',u'enContinue'],
	'planifié'          :[u'planned',u'planifié'],
	'requis'            :[u'required',u'requis'],
	'enProduction'      :[u'underDevelopment',u'enProduction'],
	'proposé'           :[u'proposed',u'proposé']
}

napDS_AssociationTypeCode = {
	'crossReference'                :[u'crossReference',u'référenceCroisée'],
	'largerWorkCitation'            :[u'largerWorkCitation',u'référenceGénérique'],
	'partOfSeamlessDatabase'        :[u'partOfSeamlessDatabase',u'partieDeBaseDeDonnéesContinue'],
	'stereoMate'                    :[u'stereoMate',u'stéréoAssociée'],
	'isComposedOf'                  :[u'isComposedOf',u'estComposéDe'],	
	'référenceCroisée'              :[u'crossReference',u'référenceCroisée'],
	'référenceGénérique'            :[u'largerWorkCitation',u'référenceGénérique'],
	'partieDeBaseDeDonnéesContinue' :[u'partOfSeamlessDatabase',u'partieDeBaseDeDonnéesContinue'],
	'stéréoAssociée'                :[u'stereoMate',u'stéréoAssociée'],
	'estComposéDe'                  :[u'isComposedOf',u'estComposéDe']
}

napMD_SpatialRepresentationTypeCode = {
	'Vector'                        :[u'Vector',                 u'Vecteur'],
	'Grid'                          :[u'Grid',                   u'Grille'],
	'Text Table'                    :[u'Text Table',             u'Texte table'],
	'Tin'                           :[u'Tin',                    u'Tin'],
	'Stero Model'                   :[u'Stero Model',            u'Stéréomodèle'],
	'Video'                         :[u'Video',                  u'Vidéo'],
	'Vecteur'                       :[u'Vector',                 u'Vecteur'],
	'Grille'                        :[u'Grid',                   u'Grille'],
	'Texte table'                   :[u'Text Table',             u'Texte table'],
	'Stéréomodèle'                  :[u'Stero Model',            u'Stéréomodèle'],
	'Vidéo'                         :[u'Video',                  u'Vidéo']
}

OGP_catalogueType = {
	'Data'     :[u'Data',u'Données'],
	'Geo Data' :[u'Geo Data',u'Géo'],
	'FGP Data' :[u'FGP Data',u'FGP Data'],
	'Données'  :[u'Data',u'Données'],
	'Géo'      :[u'Geo Data',u'Géo'],
	'FGP Data' :[u'FGP Data',u'FGP Data']
}

napMD_KeywordTypeCode = {
	'farming'                                     :[u'Agriculture'],
	'agriculture'                                 :[u'Agriculture'],
	'biota'                                       :[u'Nature and Environment, Science and Technology'],
	'biote'                                       :[u'Nature and Environment, Science and Technology'],
	'boundaries'                                  :[u'Government and Politics'],
	'frontières'                                  :[u'Government and Politics'],
	'climatology / meteorology / atmosphere'      :[u'Nature and Environment, Science and Technology'],
	'climatologie / météorologie / atmosphère'    :[u'Nature and Environment, Science and Technology'],
	'economy'                                     :[u'Economics and Industry'],
	'économie'                                    :[u'Economics and Industry'],
	'elevation'                                   :[u'Form Descriptors'],
	'élévation'                                   :[u'Form Descriptors'],
	'environment'                                 :[u'Nature and Environment'],
	'environnement'                               :[u'Nature and Environment'],
	'geoscientific information'                   :[u'Nature and Environment, Science and Technology, Form Descriptors'],
	'information géoscientifique'                 :[u'Nature and Environment, Science and Technology, Form Descriptors'],
	'health'                                      :[u'Health and Safety'],
	'santé'                                       :[u'Health and Safety'],
	'imagery base maps earth cover'               :[u'Form Descriptors'],
	'imagerie carte de base couverture terrestre' :[u'Form Descriptors'],
	'intelligence military'                       :[u'Military'],
	'renseignements militaires'                   :[u'Military'],
	'inland waters'                               :[u'Nature and Environment'],
	'eaux intérieures'                            :[u'Nature and Environment'],
	'location'                                    :[u'Form Descriptors'],
	'localisation'                                :[u'Form Descriptors'],
	'oceans'                                      :[u'Nature and Environment'],
	'océans'                                      :[u'Nature and Environment'],
	'planning cadastre'                           :[u'Nature and Environment, Form Descriptors, Economics and Industry'],
	'aménagement cadastre'                        :[u'Nature and Environment, Form Descriptors, Economics and Industry'],
	'society'                                     :[u'Society and Culture'],
	'société'                                     :[u'Society and Culture'],
	'structure'                                   :[u'Economics and Industry'],
	'structures'                                  :[u'Economics and Industry'],
	'transportation'                              :[u'Transport'],
	'transport'                                   :[u'Transport'],
	'utilities communication'                     :[u'Economics and Industry, IN Information and Communications'],
	'services communication'                      :[u'Economics and Industry, IN Information and Communications']
}

napMD_MaintenanceFrequencyCode = {
	'As Needed'   :[u'As_Needed',u'Au_besoin'],
	'Continual'   :[u'Continual',u'Continue'],
	'Daily'       :[u'Daily',u'Quotidien'],
	'Weekly'      :[u'Weekly',u'Hebdomadaire'],
	'Fortnightly' :[u'Fortnightly',u'Quinzomadaire'],
	'Monthly'     :[u'Monthly',u'Mensuel'],
	'Semimonthly' :[u'Semimonthly',u'Bimensuel'],
	'Quarterly'   :[u'Quarterly',u'Trimestriel'],
	'Biannually'  :[u'Biannually',u'Semestriel'],
	'Annually'    :[u'Annually',u'Annuel'],
	'Irregular'   :[u'Irregular',u'Irrégulier'],
	'Not Planned' :[u'Not_Planned',u'Non_planifié'],
	'Unknown'     :[u'Unknown',u'Inconnu'],

	'Au besoin'   :[u'As_Needed',u'Au_besoin'],
	'Continue'    :[u'Continual',u'Continue'],
	'Daily'       :[u'Daily',u'Quotidien'],
	'Weekly'      :[u'Weekly',u'Hebdomadaire'],
	'Fortnightly' :[u'Fortnightly',u'Quinzomadaire'],
	'Monthly'     :[u'Monthly',u'Mensuel'],
	'Semimonthly' :[u'Semimonthly',u'Bimensuel'],
	'Quarterly'   :[u'Quarterly',u'Trimestriel'],
	'Biannually'  :[u'Biannually',u'Semestriel'],
	'Annually'    :[u'Annually',u'Annuel'],
	'Irregular'   :[u'Irregular',u'Irrégulier'],
	'Not Planned' :[u'Not_Planned',u'Non_planifié'],
	'Unknown'     :[u'Unknown',u'Inconnu']

}

## In the mapping doc but not used
#presentationForm = {
#	'Document Digital'      :[u'Document Digital',u'Document numérique'],
#	'Document Hardcopy'     :[u'Document Hardcopy',u'Document papier'],
#	'Image Digital'         :[u'Image Digital',u'Image numérique'],
#	'Image Hardcopy'        :[u'Image Hardcopy',u'Image papier'],
#	'Map Digital'           :[u'Map Digital',u'Carte numérique'],
#	'Map Hardcopy'          :[u'Map Hardcopy',u'Carte papier'],
#	'Model Digital'         :[u'Model Digital',u'Modèle numérique'],
#	'Model Hardcopy'        :[u'Model Hardcopy',u'Maquette'],
#	'Profile Digital'       :[u'Profile Digital',u'Profil numérique'],
#	'Profile Hardcopy'      :[u'Profile Hardcopy',u'Profil papier'],
#	'Table Digital'         :[u'Table Digital',u'Table numérique'],
#	'Table Hardcopy'        :[u'Table Hardcopy',u'Table papier'],
#	'Video Digital'         :[u'Video Digital',u'Vidéo numérique'],
#	'Video Hardcopy'        :[u'Video Hardcopy',u'Vidéo film'],
#	'Audio Digital'         :[u'Audio Digital',u'Audio numérique'],
#	'Audio Hardcopy'        :[u'Audio Hardcopy',u'Audio analogique'],
#	'Multimedia Digital'    :[u'Multimedia Digital',u'Multimédia numérique'],
#	'Multimedia Hardcopy'   :[u'Multimedia Hardcopy',u'Multimédia analogique'],
#	'Diagram Digital'       :[u'Diagram Digital',u'Diagramme numérique'],
#	'Diagram Hardcopy'      :[u'Diagram Hardcopy',u'Diagramme papier'],
#	'Document numérique'    :[u'Document Digital',u'Document numérique'],
#	'Document papier'       :[u'Document Hardcopy',u'Document papier'],
#	'Image numérique'       :[u'Image Digital',u'Image numérique'],
#	'Image papier'          :[u'Image Hardcopy',u'Image papier'],
#	'Carte numérique'       :[u'Map Digital',u'Carte numérique'],
#	'Carte papier'          :[u'Map Hardcopy',u'Carte papier'],
#	'Modèle numérique'      :[u'Model Digital',u'Modèle numérique'],
#	'Maquette'              :[u'Model Hardcopy',u'Maquette'],
#	'Profil numérique'      :[u'Profile Digital',u'Profil numérique'],
#	'Profil papier'         :[u'Profile Hardcopy',u'Profil papier'],
#	'Table numérique'       :[u'Table Digital',u'Table numérique'],
#	'Table papier'          :[u'Table Hardcopy',u'Table papier'],
#	'Vidéo numérique'       :[u'Video Digital',u'Vidéo numérique'],
#	'Vidéo film'            :[u'Video Hardcopy',u'Vidéo film'],
#	'Audio numérique'       :[u'Audio Digital',u'Audio numérique'],
#	'Audio analogique'      :[u'Audio Hardcopy',u'Audio analogique'],
#	'Multimédia numérique'  :[u'Multimedia Digital',u'Multimédia numérique'],
#	'Multimédia analogique' :[u'Multimedia Hardcopy',u'Multimédia analogique'],
#	'Diagramme numérique'   :[u'Diagram Digital',u'Diagramme numérique'],
#	'Diagramme papier'      :[u'Diagram Hardcopy',u'Diagramme papier']
#}

if __name__    == "__main__":
	sys.exit(main())
