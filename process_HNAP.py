#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import codecs
from lxml import etree
import re
import time
import json
import os
import csv

output_human = False
output_json  = True

global_json = {}

# Report Header
iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
if output_human:
	print "======================================================================"
	print "= ... :: "+iso_time+" ======================================="
	print "======================================================================"
	print "==== (M)   Mandatory ================================================="
	print "==== (M/a) Mandatory if Applicable ==================================="
	print "==== (O)   Optional==================================================="
	print "==== (M-C) Mandatory, CKAN generated ================================="
	print "======================================================================"

json_output = []
input_files = [
#	'data/TBS_V2/tst.xml'
	'data/TBS_V2/aplCANreg_metadata_HNAP_exemple_minimum.xml',
	'data/TBS_V2/aplCANreg_metadata_HNAP_exemple.xml',
#	'data/TBS_V2/metadata_HNAP_exemple_minimum.xml',
#	'data/TBS_V2/NRN_metadata_HNAP_exemple .xml'
]
#input_files = ['series-series.xml']

global_json = {}

for input_file in input_files:

	# Report import file marker
	if output_human:
		print "======================================================================"
		print "===== "+input_file
		print "======================================================================"


	#f = codecs.open(input_file, "r", "utf-8")

	#print f.read()
	#break

	#ValueError: Unicode strings with encoding declaration are not supported.
	#xml = f.read()#.encode('utf-8')
	#parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
	#root = etree.fromstring(f.read())
	
	root = etree.parse(input_file)

	#for record in root.xpath("/gmd:MD_Metadata/gmd:fileIdentifie"):
	for record in root.xpath("/gmd:MD_Metadata", namespaces={'gmd':'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco'}):

		json_record = {}
		json_record['resources'] = [{}]
		json_record['type'] ='geo_or_fgp?'
		json_record['license_id'] = 'ca-ogl-lgo'

		def genericOut( name, xpath, pattern='', replace=''):
			global output_human
			value = None
			r = record.xpath(xpath, namespaces={'gmd':'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco','gml':'http://www.opengis.net/gml/3.2'})
			if(len(r)):
				for namePart in r:
					#print namePart
					#print 'xxxxx'+namePart.text
					if(namePart.text == None):
						if output_human:
							print "-blank----:"+name
						return None
					else:
						value = namePart.text.strip()
						if(len(name)):
							if pattern != '':
								p = re.compile(pattern)
								value = p.sub( replace, value)
							if output_human:
								print name+":"+value
			else:
				if(len(name)):
					if output_human:
						print "-missing----:"+name
					return None
			return value

		CRecord_primary_language = genericOut('1.    fileIdentifier',"gmd:language/gco:CharacterString")
		CRecord_primary_language = CRecord_primary_language.strip().split(';')[0]
		print CRecord_primary_language
		if CRecord_primary_language == 'eng':
			CRecord_secondary_language = 'fra'
		else:
			CRecord_secondary_language = 'eng'
		#continue
		CRecord_id = genericOut('1.    fileIdentifier',"gmd:fileIdentifier/gco:CharacterString")
		json_record['id'] = CRecord_id
		if output_human:
			print      '2.    shortKey - UDEFINED'
		genericOut('3.    metadataRecordLanguage',"gmd:language/gco:CharacterString")
		genericOut('4.    characterSet',"gmd:characterSet/gmd:MD_CharacterSetCode")
		json_record['parent_id'] = genericOut('5.    parentIdentifier',"gmd:parentIdentifier/gco:CharacterString")
		value = genericOut('6.    hierarchyLevel',"gmd:hierarchyLevel/gmd:MD_ScopeCode")
		if value != None:
			(primary,secondary) = value.strip().split(';')
			json_record['hierarchy_level'] = {}
			json_record['hierarchy_level'][CRecord_primary_language] = primary
			json_record['hierarchy_level'][CRecord_secondary_language] = secondary
			if output_human:
				print      '6a.   '+primary.strip()
				print      '6b.   '+secondary.strip()
		genericOut('7a1.  organisationName',"gmd:contact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString")
		genericOut('7a2.  organizationName-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:organisationName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		genericOut('7b1.  voice',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString")
		genericOut('7b2.  voice-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		genericOut('7c1.  electronicMailAddress',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString")
		genericOut('7c2.  electronicMailAddress-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		genericOut('8.    metadataRecordDateStamp',"gmd:dateStamp/gco:Date")
		if output_human:
			print      '9-eng metadataStandard:Government of Canada’s Open Geospatial Data Metadata Element Set'
			print      '9-fra metadataStandard:Données ouvertes géospatiales du gouvernement du Canada – Ensemble d’éléments de métadonnées'
			print      '10.   Metadata URI:Metadata URI .... GeoNetworkServer/csw?service=CSW&version=2.0.2&request=GetRecordById&outputSchema=csw:IsoRecord&id=698ea2e7-8025-481b-a011-7ff6232939aa'
		value = genericOut('11.   locale',"gmd:MD_Metadata/gmd:locale/gmd:PT_Locale/gmd:languageCode/gmd:LanguageCode")
		if value != None:
			(primary,secondary) = value.strip().split(';')
			if output_human:
				print      '11a.  '+primary.strip()
				print      '11b.  '+secondary.strip()
		json_record['title'] = {}
		json_record['title'][CRecord_primary_language]   = genericOut('12a.  title',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString")
		json_record['title'][CRecord_secondary_language] = genericOut('12b.  title-Alt',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if output_human:
			print "13.   dateContributed: CKAN SUPPLIED"
		r = record.xpath("gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date", namespaces={'gmd':'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco'})
		if(len(r)):
			for cn in r:
				if cn[1][0].text == u'publication; publication':
					json_record['date_published'] = cn[0][0].text.strip()
					if output_human:
						print "14.   datePublished:"+cn[0][0].text.strip()
				if cn[0][0].text == u'publication; publication':
					json_record['date_published'] = cn[1][0].text.strip()
					if output_human:
						print "14.   datePublished:"+cn[1][0].text.strip()
				if cn[1][0].text == u'revision; révision':
					json_record['date_modified'] = cn[0][0].text.strip()
					if output_human:
						print "15.   dateModified:"+cn[0][0].text.strip()
				if cn[0][0].text == u'revision; révision':
					json_record['date_modified'] = cn[1][0].text.strip()
					if output_human:
						print "15.   dateModified:"+cn[1][0].text.strip()
		json_record['digital_object_identifier'] = genericOut('16.  not-in-sample-----identifier',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString")
		json_record['individual_name'] = genericOut('17.  not-in-sample-----individualName',"gmd:contact/gmd:CI_ResponsibleParty/gmd:individualName/gco:CharacterString")
		json_record['responsible_organization'] = {}
		value = genericOut('18a.  organisationName',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString")
		if value != None:
			values = value.strip().split(';')
			if values[0] != 'Government of Canada' and values[0] != 'Gouvernement du Canada':
				print "ERROR: BAD organizationName"
			del values[0]
			for GOC_Div in values:
				json_record['responsible_organization'][CRecord_primary_language] = GOC_Div.strip()
				if output_human:
					print '18ax. '+GOC_Div.strip()
		genericOut('18b.  organisationName-Alt',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty/gmd:organisationName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		if value != None:
			values = value.strip().split(';')
			if values[0] != 'Government of Canada' and values[0] != 'Gouvernement du Canada':
				if output_human:
					print "ERROR: BAD organizationName"
			del values[0]
			for GOC_Div in values:
				json_record['responsible_organization'][CRecord_secondary_language] = GOC_Div.strip()
				if output_human:
					print '18bx. '+GOC_Div.strip()
		
		json_record['position_name'] = {}
		genericOut('19a.  not-in-sample-----positionName',"gmd:contact/gmd:CI_ResponsibleParty/gmd:positionName/gco:CharacterString")
		genericOut('19b.  not-in-sample-----positionName-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:positionName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		
		genericOut('20a1.  contactInfo-deliveryPoint',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:deliveryPoint/gco:CharacterString")
		genericOut('20a2.  contactInfo-deliveryPoint-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:deliveryPoint/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		genericOut('20b1.  contactInfo-CI_Address',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:city/gco:CharacterString")
		genericOut('20b1.  contactInfo-CI_Address-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:city/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		genericOut('20c1.  contactInfo-administrativeArea',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:administrativeArea/gco:CharacterString")
		genericOut('20c1.  contactInfo-administrativeArea-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:administrativeArea/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		genericOut('20d1.  contactInfo-postalCode',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:postalCode/gco:CharacterString")
		genericOut('20d1.  contactInfo-postalCode-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:postalCode/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		genericOut('20e1.  contactInfo-country',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:country/gco:CharacterString")
		genericOut('20e1.  contactInfo-country-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:country/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		genericOut('20f1.  contactInfo-electronicMailAddress',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString")
		genericOut('20f1.  contactInfo-electronicMailAddress-Alt',"gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		value = genericOut('21.  role',"gmd:contact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode")
		json_record['responsible_role'] = {}
		if value != None:
			(primary,secondary) = value.strip().split(';')
			json_record['responsible_role'][CRecord_primary_language] = primary
			json_record['responsible_role'][CRecord_secondary_language] = secondary
			if output_human:
				print      '21a.  '+primary.strip()
				print      '21b.  '+secondary.strip()
		
		json_record['notes'] = {}
		json_record['notes'][CRecord_primary_language]   = genericOut('22a.  abstract',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString")
		json_record['notes'][CRecord_secondary_language] = genericOut('22b.  abstract-Alt',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString")
		
		json_record['kekywords'] = {}
		json_record['kekywords'][CRecord_primary_language]   = genericOut('23ax. descriptiveKeywords',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString",'^[A-Z][A-Z] [^>]+ > ')
		json_record['kekywords'][CRecord_secondary_language] = genericOut('23bx. descriptiveKeywords-Alt',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString",'^[A-Z][A-Z] [^>]+ > ')
		
		json_record['status'] = {}
		value = genericOut('24.   status',"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode")
		if value != None:
			(primary,secondary) = value.strip().split(';')
			json_record['status'][CRecord_primary_language]   = primary.strip()
			json_record['status'][CRecord_secondary_language] = secondary.strip()
			if output_human:
				print      '24a.  '+primary.strip()
				print      '24b.  '+secondary.strip()

		genericOut('25.   not-in-sample-----associationType',"gmd:aggregationInfo/gmd:MD_AggregateInformation/gmd:associationType/gmd:DS_AssociationTypeCode")
		json_record['association_type'] {'NOSAMPLES'}
		genericOut('26.   not-in-sample-----aggregateDataSetIdentifier',"gmd:aggregationInfo/gmd:MD_AggregateInformation/gmd:aggregateDataSetIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString")
		json_record['aggregate_identifier'] {'NOSAMPLES'}

		json_record['spatial_representation_type'] = {}
		value = genericOut('27.   spatialRepresentationType','gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialRepresentationType/gmd:MD_SpatialRepresentationTypeCode')
		if value != None:
			(primary,secondary) = value.strip().split(';')
			json_record['spatial_representation_type'][CRecord_primary_language]   = primary.strip()
			json_record['spatial_representation_type'][CRecord_secondary_language] = secondary.strip()
			if output_human:
				print      '27a.  '+primary.strip()
				print      '27b.  '+secondary.strip()

		json_record['topic_category'] {'NOSAMPLES'}
		genericOut('28.   topicCategory','gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode')

		genericOut('29.   geographicBoundingBox - westBoundingLongitude','gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal')
		genericOut('30.   geographicBoundingBox - eastBoundingLongitude','gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal')
		genericOut('31.   geographicBoundingBox - southBoundingLongitude','gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal')
		genericOut('32.   geographicBoundingBox - northBoundingLongitude','gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal')

		json_record['time_period_coverage_start'] = genericOut('33a.  temporalElement-begin','gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition')
		json_record['time_period_coverage_end']   = genericOut('33b.  temporalElement-end','gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition')		

		json_record['frequency'] = {}
		value = genericOut('34.   maintenanceAndUpdateFrequency','gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode')
		if value != None:
			(primary,secondary) = value.strip().split(';')
			json_record['frequency'][CRecord_primary_language]   = primary.strip()
			json_record['frequency'][CRecord_secondary_language] = secondary.strip()
			if output_human:
				print      '34a.  '+primary.strip()
				print      '34b.  '+secondary.strip()

		if output_human:
			print "35a.   Licence:Open Government Licence – Canada <linkto: http://open.canada.ca/en/open-government-licence-canada>"
			print "35b.   Licence:Licence du gouvernement ouvert – Canada <linkto : http://ouvert.canada.ca/fr/licence-du-gouvernement-ouvert-canada>"

		vala = genericOut('36a.   referenceSystemInformation-code','gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString')
		valb = genericOut('36b.   referenceSystemInformation-codespace','gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString')
		valc = genericOut('36c.   referenceSystemInformation-version','gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:version/gco:CharacterString')
		reference_system = '"'+vala+'","'+valb+'","'+valc+'"'
		json_record['reference_system'] = reference_system
		if output_human:
			print '36abc.    reference:'+reference_system

		json_record['distributor'] = {}
		vala = genericOut('37a.   distributor-name','gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString')
		valb = genericOut('37b.   distributor-email','gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString')
		json_record['distributor'][CRecord_primary_language] = vala
		json_record['distributor'][CRecord_secondary_language] = valb
		if output_human:
			print '37ab.    distributor:"'+vala+'","'+valb+'"'

		value = genericOut('37c.   distributor-bilingualrole','gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode')
		if value != None:
			(primary,secondary) = value.strip().split(';')
			if output_human:
				print      '37c1.  '+primary.strip()
				print      '37c2.  '+secondary.strip()
		genericOut('37d.   distributor-name-Alt','gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:organisationName/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString')
		genericOut('37e.   distributor-email-Alt','gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString')
		value = genericOut('37f.   distributor-bilingualrole-Alt','gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode')
		if value != None:
			(primary,secondary) = value.strip().split(';')
			if output_human:
				print      '37f1.  '+primary.strip()
				print      '37f2.  '+secondary.strip()
		if output_human:
			print "38.  CatalogueType: FGP"
		genericOut('39a.   ResourceName','gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:name/gco:CharacterString')
		genericOut('39b.   ResourceName-Alt','gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:name/gmd:PT_FreeText/gmd:textGroup/gmd:LocalisedCharacterString')
		genericOut('40x.    accessURL','gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:linkage/gmd:URL')
		###### format
		###### language
		###### contentType
		#genericOut('-incomplete-----description','gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:description/gco:CharacterString')
		if output_human:
			print "41.   Format:TBD"
			print "42.   Language:TBD"
			print "43.   Content Type:TBD"

		if output_json:
			global_json[CRecord_id] = json_record

	#break
	continue

for key, value in global_json.iteritems() :
	#global_json[] json.dumps(json_record)
	#print json.dumps(json_record, sort_keys=True, indent=4, separators=(',', ': '))
	print json.dumps(value)



