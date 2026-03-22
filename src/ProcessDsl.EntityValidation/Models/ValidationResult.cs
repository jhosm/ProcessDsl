using Newtonsoft.Json;

namespace ProcessDsl.EntityValidation.Models;

public class ValidationResult
{
    [JsonProperty("isValid")]
    public bool IsValid { get; set; }

    [JsonProperty("errors")]
    public List<string> Errors { get; set; } = new();

    [JsonProperty("entityName")]
    public string EntityName { get; set; } = "unknown";

    [JsonProperty("entityModel")]
    public string EntityModel { get; set; } = "unknown";
}
