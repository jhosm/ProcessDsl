using ProcessDsl.EntityValidation.Models;

namespace ProcessDsl.EntityValidation;

public interface IEntitySchemaValidator
{
    ValidationResult Validate(object? processEntity, string? entityName, string? entityModel);
}
