# Lidia config help

The structure of configuration object is defined as the `Config` class in config.py file.

## Config files

Every time a configuration file is passed, fields in config objects are copied and then overwritten by the config file. This means there is no need to provide every property, only the ones to be changed.

In case more than one file is passed, the first will be applied on top of defaults, and then the latter will override any present values, either left as default, or from first the file.

To prevent silently failing in case of a mistyped key, every property is validated, both for name and type. To help with writing configuration, template files can be generated for each supported format by using this source. The template includes address of the JSON Schema file that describes the structure, allowing a text editor to provide hints. You need to run the confighelp source at least once to generate the schema (the schema generation requires `pydantic` so it isn't part of package build).

By default the schema URL contains full path to the installed data folder. When sharing the configuration files, you might want to set it to:

- local path relative to config file, like "lidia-config.json" if they are in same directory. (note lack of `file:` prefix)

## Config-keys argument

After all config files are processed, values can be overriden using CLI arguments. To do that pass a set of properties like

```
group.innergroup.value="string value, in quotes",group.innergroup.value2=2.0
```
