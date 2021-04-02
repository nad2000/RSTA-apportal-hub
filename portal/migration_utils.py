def disable_constraints(apps, schema_editor):
    engine = schema_editor.connection.settings_dict.get("ENGINE").split(".")[-1]
    if engine == "sqlite3":
        schema_editor.execute("PRAGMA foreign_keys = OFF;")
    # else:
    #     schema_editor.execute("SET FOREIGN_KEY_CHECKS=0;")


def enable_constraints(apps, schema_editor):
    engine = schema_editor.connection.settings_dict.get("ENGINE").split(".")[-1]
    if engine == "sqlite3":
        schema_editor.execute("PRAGMA foreign_keys = ON;")
    # else:
    #     schema_editor.execute("SET FOREIGN_KEY_CHECKS=1;")
