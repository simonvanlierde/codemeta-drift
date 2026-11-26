# Documentation

codemeta-drift shows where CodeMeta's crosswalk cells for citation and package formats work as
written and where they don't: [see every cell](https://simonvanlierde.com/codemeta-drift/). It
also checks CodeMeta's own files against each other, and exports a reviewed JSON field mapping for
tools such as [citesync](https://github.com/simonvanlierde/citesync).

It is not part of the CodeMeta project. Its `identifier` column means the software's DOI, narrower
than CodeMeta's "any kind of identifier". The [README](https://github.com/simonvanlierde/codemeta-drift#try-it)
shows how to run the command.

- [Coverage](coverage.md): the crosswalk matrix for each CodeMeta release, and what each count covers.
- [Findings](findings.md): what the checks found in earlier CodeMeta snapshots.
- [Mapping export](mapping-export.md): the JSON contract consumers pin, and
  [how to read each format's paths](reading-formats.md).
- [Crosswalk hub](crosswalk-hub.md): corresponding fields between two formats, and the SSSOM export;
  [SSSOM compatibility](sssom-compatibility.md) compares it with CodeMeta's methodology.
- [Schema watcher](schema-watcher.md): previewing format schema changes, with
  [Zenodo path coverage](zenodo-schema.md) and [a rename from finding to fix](schema-recovery.md).
- [Checks reference](checks.md): finding codes, compared files, exit codes and JSON output.
- [Development](development.md): tests, the site, the schema watcher's publishing and the social card.
- [Decisions](decisions/README.md): records of project choices.
