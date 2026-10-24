-- El ejecutor expande estas sentencias solo con grupos validados de project.json.
GRANT USE CATALOG ON CATALOG workspace TO {principal};
GRANT USE SCHEMA ON SCHEMA {namespace} TO {principal};
GRANT SELECT ON {object_type} {object_name} TO {principal};
