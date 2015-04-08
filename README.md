# hand-converted hnap XML to JSON examples

See [issue #1](https://github.com/open-data/hnap/issues/1) for info
about encoding oddities in the XML.

## missing fields

In the json examples I've included a number of fields that are not
present in the XML source, just to show you that these fields do exist
in our schema. Things that look like:

```json
{
    "date_modified": null,
    "association_type": [],
    "position_name": {
        "en": null,
        "fr": null
    },
    "keywords": {
        "en": [],
        "fr": []
    }
}
```

If no data is present it's not necessary to provide these fields
in the json.

The `date_modified` above would be a simple string value.

The `association_type` list above would contain strings values.

The `position_name` object above would contain simple strings for each language present.

The `keywords` object above would contain lists of string values.

## mapping

| OGDMES FINAL DRAFT | ckan field |
| --- | --- |
| fileIdentifier | id |
| metadataRecordLanguage | |
| characterSet | |
| parentIdentifier | parent_id |
| hierarchyLevel | hierarchy_level |
| metadataContactEnglish | |
| metadataContactFrench | |
| metadataRecordDateStamp | (created by ckan) |
| metadataStandardName | |
| metadataURI | url |
| locale | |
| title english | title.en |
| title french | title.fr |
| dateContributed | (created by ckan) |
| datePublished | date_published |
| dateModified | date_modified |
| identifier | digital_object_identifier |
| individualName | individual_name |
| organisationNameEnglish | responsible_organization.en |
| organisationNameFrench | responsible_organization.fr |
| positionNameEnglish | position_name.en |
| positionNameFrench | position_name.fr |
| contactInfo-deliveryPoint | contact_delivery_point |
| contactInfo-CI_Address | contact_address |
| contactInfo-administrativeArea | contact_administrative_area |
| contactInfo-postalCode | contact_postal_code |
| contactInfo-country | contact_country |
| contactInfo-electronicMailAddress | maintainer_email |
| role | responsible_role |
| abstractEnglish | notes.en |
| abstractFrench | notes.fr |
| descriptiveKeywordsEnglish | keywords.en[] |
| descriptiveKeywordsFrench | keywords.fr[] |
| status | status |
| associationType | association_type[] |
| aggregateDataSetIdentifier | aggregate_identifier[] |
| spatialRepresentationType | spatial_representation_type[] |
| topicCategory | topic_category[] |
| westBoundingLongitude | spatial (as geojson string) |
| eastBoundingLongitude | |
| southBoundingLatitude | |
| northBoundingLatitude | |
| temporalElement | time_period_coverage_start, time_period_coverage_end |
| maintenanceAndUpdateFrequency | frequency |
| licence | license_id |
| referenceSystemInformation | reference_system |
| distributorEnglish | distributor.en |
| distributorFrench | distributor.fr |
| catalogueType | type (always = 'geo') |
| ResourceNameEnglish | resources[].name.en |
| ResourceNameFrench | resources[].name.fr |
| accessURL | resources[].url |
| format | resources[].format |
| language | resources[].language |
| contentType | resources[].content |
