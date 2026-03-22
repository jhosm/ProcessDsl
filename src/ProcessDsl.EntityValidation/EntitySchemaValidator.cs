using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NJsonSchema;
using ProcessDsl.EntityValidation.Models;
using YamlDotNet.Serialization;

namespace ProcessDsl.EntityValidation;

public class EntitySchemaValidator : IEntitySchemaValidator
{
    private readonly string _contractsBaseDir;
    private readonly ILogger<EntitySchemaValidator> _logger;

    public EntitySchemaValidator(
        IOptions<EntityValidationConfiguration> config,
        ILogger<EntitySchemaValidator> logger)
    {
        _logger = logger;

        var baseDir = config.Value.ContractsBaseDir;
        _contractsBaseDir = Path.IsPathRooted(baseDir)
            ? baseDir
            : Path.Combine(AppContext.BaseDirectory, baseDir);
    }

    public ValidationResult Validate(object? processEntity, string? entityName, string? entityModel)
    {
        // Check processEntity exists and is an object
        if (processEntity is null || processEntity is not JObject)
        {
            var typeDesc = processEntity?.GetType().Name ?? "null";
            _logger.LogWarning("Invalid processEntity data. Expected object, got: {Type}", typeDesc);
            return new ValidationResult
            {
                IsValid = false,
                Errors = { $"Invalid processEntity data. Expected object, got: {typeDesc}" },
                EntityName = entityName ?? "unknown",
                EntityModel = entityModel ?? "unknown"
            };
        }

        // Check entityName header
        if (string.IsNullOrEmpty(entityName))
        {
            _logger.LogWarning("Missing required header: entityName");
            return new ValidationResult
            {
                IsValid = false,
                Errors = { "Missing entityName in task headers" },
                EntityName = "unknown",
                EntityModel = entityModel ?? "unknown"
            };
        }

        // Check entityModel header
        if (string.IsNullOrEmpty(entityModel))
        {
            _logger.LogWarning("Missing required header: entityModel");
            return new ValidationResult
            {
                IsValid = false,
                Errors = { "Missing entityModel in task headers" },
                EntityName = entityName,
                EntityModel = "unknown"
            };
        }

        // Normalize path (strip leading slashes for security)
        var normalizedModel = entityModel.TrimStart('/');
        var modelPath = Path.GetFullPath(Path.Combine(_contractsBaseDir, normalizedModel));

        // Check file exists
        if (!File.Exists(modelPath))
        {
            _logger.LogWarning("OpenAPI model not found at: {Path}", modelPath);
            return new ValidationResult
            {
                IsValid = false,
                Errors = { $"OpenAPI model not found at: {modelPath}" },
                EntityName = entityName,
                EntityModel = entityModel
            };
        }

        try
        {
            // Load and parse the OpenAPI spec
            var raw = File.ReadAllText(modelPath);
            var openApiSpec = ParseSpec(modelPath, raw);

            // Extract entity schema from components.schemas
            var schemas = openApiSpec["components"]?["schemas"] as JObject;
            if (schemas is null || schemas[entityName] is null)
            {
                throw new InvalidOperationException($"Entity '{entityName}' not found in OpenAPI schema");
            }

            // Build a self-contained JSON Schema with definitions for $ref resolution
            var entitySchemaToken = schemas[entityName]!;
            var schemaWithDefs = (JObject)entitySchemaToken.DeepClone();

            // Add all sibling schemas as $defs for $ref resolution
            var defs = new JObject();
            foreach (var prop in schemas.Properties())
            {
                defs[prop.Name] = prop.Value.DeepClone();
            }

            // Rewrite $ref from "#/components/schemas/X" to "#/$defs/X"
            RewriteRefs(schemaWithDefs);
            foreach (var def in defs.Properties())
            {
                if (def.Value is JObject defObj)
                    RewriteRefs(defObj);
            }

            schemaWithDefs["$defs"] = defs;

            // Parse and validate with NJsonSchema
            var schemaJson = schemaWithDefs.ToString();
            var schema = JsonSchema.FromJsonAsync(schemaJson).GetAwaiter().GetResult();
            var entityJson = ((JObject)processEntity).ToString();
            var validationErrors = schema.Validate(entityJson);

            if (validationErrors.Count == 0)
            {
                _logger.LogInformation("Validation result: VALID");
                return new ValidationResult
                {
                    IsValid = true,
                    EntityName = entityName,
                    EntityModel = entityModel
                };
            }

            var errors = validationErrors
                .Select(e =>
                {
                    var path = string.IsNullOrEmpty(e.Path) ? e.Property : e.Path;
                    if (!string.IsNullOrEmpty(path) && !path.StartsWith("/"))
                        path = "/" + path;
                    return $"{path}: {e.Kind}";
                })
                .ToList();

            _logger.LogInformation("Validation result: INVALID ({Count} errors)", errors.Count);
            return new ValidationResult
            {
                IsValid = false,
                Errors = errors,
                EntityName = entityName,
                EntityModel = entityModel
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Validation error");
            return new ValidationResult
            {
                IsValid = false,
                Errors = { $"Validation error: {ex.Message}" },
                EntityName = entityName,
                EntityModel = entityModel
            };
        }
    }

    private static JObject ParseSpec(string path, string raw)
    {
        var ext = Path.GetExtension(path).ToLowerInvariant();
        if (ext == ".yaml" || ext == ".yml")
        {
            return ParseYaml(raw);
        }
        if (ext == ".json")
        {
            return JObject.Parse(raw);
        }

        // Try YAML first, then JSON
        try { return ParseYaml(raw); }
        catch { return JObject.Parse(raw); }
    }

    private static JObject ParseYaml(string yaml)
    {
        var deserializer = new DeserializerBuilder().Build();
        var yamlObject = deserializer.Deserialize(new StringReader(yaml));
        var json = JsonConvert.SerializeObject(yamlObject);
        return JObject.Parse(json);
    }

    private static void RewriteRefs(JToken token)
    {
        if (token is JObject obj)
        {
            if (obj["$ref"] is JValue refVal && refVal.Value is string refStr
                && refStr.StartsWith("#/components/schemas/"))
            {
                refVal.Value = refStr.Replace("#/components/schemas/", "#/$defs/");
            }

            foreach (var prop in obj.Properties())
                RewriteRefs(prop.Value);
        }
        else if (token is JArray arr)
        {
            foreach (var item in arr)
                RewriteRefs(item);
        }
    }
}
