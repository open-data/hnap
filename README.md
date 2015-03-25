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
