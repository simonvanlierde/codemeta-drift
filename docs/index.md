# Documentation

codemeta-drift checks CodeMeta's own files: where its context, definitions, property table,
examples and crosswalks disagree, and which crosswalk cells are wrong or missing. It also
exports the reviewed crosswalks as a JSON mapping for tools such as
[citesync](https://github.com/simonvanlierde/citesync).

The [coverage page](https://simonvanlierde.com/codemeta-drift/) shows every cell. To install and
run the command, see the [README](https://github.com/simonvanlierde/codemeta-drift#try-it).

- [Checks](checks.md): finding codes, compared files, exit codes and JSON output.
- [Findings](findings.md): what the checks found in earlier CodeMeta snapshots.
- [Coverage](coverage.md): the crosswalk matrix for each CodeMeta release.
- [Mapping export](mapping-export.md): the JSON contract consumers pin.
- [Crosswalk hub](crosswalk-hub.md): corresponding fields between two formats, and the SSSOM export.
- [SSSOM compatibility](sssom-compatibility.md): validating the export and how it compares with CodeMeta's methodology.
- [Schema watcher](schema-watcher.md): the weekly check of the format schemas, and [Zenodo path coverage](zenodo-schema.md).
- [Schema recovery](schema-recovery.md): an offline rename, from the first finding to a reviewed fix.
- [Development](development.md): tests, mutation testing and the site.
- [Decisions](decisions/README.md): the records of choices that shape the project.
