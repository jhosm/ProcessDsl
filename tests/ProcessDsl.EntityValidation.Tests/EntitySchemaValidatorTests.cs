using FluentAssertions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Moq;
using Newtonsoft.Json.Linq;
using ProcessDsl.EntityValidation.Models;
using Xunit;

namespace ProcessDsl.EntityValidation.Tests;

public class EntitySchemaValidatorTests
{
    private readonly EntitySchemaValidator _validator;
    private readonly string _testDataDir;

    public EntitySchemaValidatorTests()
    {
        _testDataDir = Path.Combine(AppContext.BaseDirectory, "TestData");
        var config = Options.Create(new EntityValidationConfiguration
        {
            ContractsBaseDir = _testDataDir
        });
        var logger = new Mock<ILogger<EntitySchemaValidator>>();
        _validator = new EntitySchemaValidator(config, logger.Object);
    }

    // === Requirement: Input Extraction ===

    [Fact]
    public void AllInputsPresent_ProceedsWithValidation()
    {
        var entity = JObject.FromObject(new { id = "1", name = "John", email = "john@example.com" });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeTrue();
    }

    [Fact]
    public void MissingProcessEntity_ReturnsInvalid()
    {
        var result = _validator.Validate(null, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeFalse();
        result.Errors.Should().ContainSingle().Which.Should().Contain("Invalid processEntity data");
    }

    [Fact]
    public void ProcessEntityNotAnObject_ReturnsInvalid()
    {
        // Pass a string instead of an object
        var result = _validator.Validate("not-an-object", "Customer", "customer-api.yaml");
        result.IsValid.Should().BeFalse();
        result.Errors.Should().ContainSingle().Which.Should().Contain("Invalid processEntity data");
    }

    [Fact]
    public void MissingEntityNameHeader_ReturnsInvalid()
    {
        var entity = JObject.FromObject(new { id = "1" });
        var result = _validator.Validate(entity, null, "customer-api.yaml");
        result.IsValid.Should().BeFalse();
        result.Errors.Should().ContainSingle().Which.Should().Contain("Missing entityName");
        result.EntityName.Should().Be("unknown");
    }

    [Fact]
    public void MissingEntityModelHeader_ReturnsInvalid()
    {
        var entity = JObject.FromObject(new { id = "1" });
        var result = _validator.Validate(entity, "Customer", null);
        result.IsValid.Should().BeFalse();
        result.Errors.Should().ContainSingle().Which.Should().Contain("Missing entityModel");
        result.EntityModel.Should().Be("unknown");
    }

    // === Requirement: Schema Loading ===

    [Fact]
    public void LoadYamlSchema_ParsesSuccessfully()
    {
        var entity = JObject.FromObject(new { id = "1", name = "John", email = "john@example.com" });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeTrue();
        result.EntityModel.Should().Be("customer-api.yaml");
    }

    [Fact]
    public void LoadJsonSchema_ParsesSuccessfully()
    {
        var entity = JObject.FromObject(new { id = "1", name = "John", email = "john@example.com" });
        var result = _validator.Validate(entity, "Customer", "customer-api.json");
        result.IsValid.Should().BeTrue();
    }

    [Fact]
    public void SchemaFileNotFound_ReturnsInvalid()
    {
        var entity = JObject.FromObject(new { id = "1" });
        var result = _validator.Validate(entity, "Customer", "nonexistent.yaml");
        result.IsValid.Should().BeFalse();
        result.Errors.Should().ContainSingle().Which.Should().Contain("not found");
    }

    [Fact]
    public void PathTraversalPrevention_StripsLeadingSlash()
    {
        // Leading slash should be stripped — the resolved path should still
        // look inside the contracts base dir, not escape to root
        var entity = JObject.FromObject(new { id = "1", name = "John", email = "john@example.com" });
        var result = _validator.Validate(entity, "Customer", "/customer-api.yaml");
        result.IsValid.Should().BeTrue();
    }

    // === Requirement: Entity Schema Resolution ===

    [Fact]
    public void EntityFoundInSchema_UsesForValidation()
    {
        var entity = JObject.FromObject(new { id = "1", name = "John", email = "john@example.com" });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeTrue();
        result.EntityName.Should().Be("Customer");
    }

    [Fact]
    public void EntityNotInSchema_ReturnsInvalid()
    {
        var entity = JObject.FromObject(new { id = "1" });
        var result = _validator.Validate(entity, "NonExistent", "customer-api.yaml");
        result.IsValid.Should().BeFalse();
        result.Errors.Should().ContainSingle().Which.Should().Contain("not found in OpenAPI schema");
    }

    [Fact]
    public void CrossSchemaReferences_ResolvesViaRef()
    {
        // Customer has address: $ref: '#/components/schemas/Address'
        var entity = JObject.FromObject(new
        {
            id = "1",
            name = "John",
            email = "john@example.com",
            address = new { street = "123 Main St", city = "NYC", country = "US" }
        });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeTrue();
    }

    [Fact]
    public void CrossSchemaReferences_InvalidRef_ReportsError()
    {
        // Address missing required 'country' field
        var entity = JObject.FromObject(new
        {
            id = "1",
            name = "John",
            email = "john@example.com",
            address = new { street = "123 Main St", city = "NYC" }
        });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.Contains("country"));
    }

    // === Requirement: JSON Schema Validation ===

    [Fact]
    public void ValidEntityPasses_ReturnsIsValidTrue()
    {
        var entity = JObject.FromObject(new { id = "1", name = "John", email = "john@example.com" });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeTrue();
        result.Errors.Should().BeEmpty();
    }

    [Fact]
    public void MultipleValidationErrors_AllCollected()
    {
        // Missing all required fields: id, name, email
        var entity = new JObject();
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeFalse();
        result.Errors.Count.Should().BeGreaterThanOrEqualTo(3);
    }

    [Fact]
    public void FormatValidation_InvalidEmail_ReportsError()
    {
        var entity = JObject.FromObject(new { id = "1", name = "John", email = "not-an-email" });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.Contains("email"));
    }

    [Fact]
    public void EnumValidation_InvalidValue_ReportsError()
    {
        var entity = JObject.FromObject(new
        {
            id = "1",
            name = "John",
            email = "john@example.com",
            status = "deleted" // not in enum
        });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeFalse();
    }

    // === Requirement: Structured Validation Results ===

    [Fact]
    public void SuccessfulValidation_ReturnsCorrectStructure()
    {
        var entity = JObject.FromObject(new { id = "1", name = "John", email = "john@example.com" });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeTrue();
        result.Errors.Should().BeEmpty();
        result.EntityName.Should().Be("Customer");
        result.EntityModel.Should().Be("customer-api.yaml");
    }

    [Fact]
    public void FailedValidation_ErrorsContainPaths()
    {
        var entity = JObject.FromObject(new
        {
            id = "1",
            name = "John",
            email = "john@example.com",
            address = new { street = "123 Main St", city = "NYC" } // missing country
        });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.IsValid.Should().BeFalse();
        // Errors should reference the path to the failing field
        result.Errors.Should().Contain(e => e.Contains("country"));
    }

    [Fact]
    public void AlwaysCompletesJob_NeverThrows()
    {
        // Even with completely invalid inputs, Validate should return a result, not throw
        var entity = JObject.FromObject(new { id = "1" });
        var act = () => _validator.Validate(entity, "Customer", "corrupt-file.yaml");
        act.Should().NotThrow();
    }

    [Fact]
    public void EchoesEntityNameAndModel_InResult()
    {
        var entity = JObject.FromObject(new { id = "1", name = "John", email = "john@example.com" });
        var result = _validator.Validate(entity, "Customer", "customer-api.yaml");
        result.EntityName.Should().Be("Customer");
        result.EntityModel.Should().Be("customer-api.yaml");
    }

    [Fact]
    public void MissingInputs_DefaultToUnknown()
    {
        var result = _validator.Validate(null, null, null);
        result.EntityName.Should().Be("unknown");
        result.EntityModel.Should().Be("unknown");
    }
}
