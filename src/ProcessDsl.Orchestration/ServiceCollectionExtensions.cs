using Microsoft.Extensions.DependencyInjection;
using ProcessDsl.Orchestration.Models;

namespace ProcessDsl.Orchestration;

/// <summary>
/// Extension methods for registering ProcessDsl Orchestration services
/// </summary>
public static class ServiceCollectionExtensions
{
    /// <summary>
    /// Adds ProcessDsl orchestration services to the dependency injection container
    /// </summary>
    /// <param name="services">Service collection</param>
    /// <param name="configureOptions">Configuration action for Camunda settings</param>
    /// <returns>Service collection for chaining</returns>
    public static IServiceCollection AddProcessDslOrchestration(
        this IServiceCollection services,
        Action<CamundaConfiguration> configureOptions)
    {
        if (services == null)
            throw new ArgumentNullException(nameof(services));

        if (configureOptions == null)
            throw new ArgumentNullException(nameof(configureOptions));

        // Register configuration
        services.Configure(configureOptions);

        // Register Zeebe gRPC client as singleton
        services.AddSingleton<ICamundaClient, CamundaClient>();

        // Register orchestrator
        services.AddScoped<IProcessOrchestrator, ProcessOrchestrator>();

        return services;
    }

    /// <summary>
    /// Adds ProcessDsl orchestration services with default configuration
    /// </summary>
    /// <param name="services">Service collection</param>
    /// <param name="gatewayAddress">Zeebe gRPC gateway address (e.g., localhost:26500)</param>
    /// <returns>Service collection for chaining</returns>
    public static IServiceCollection AddProcessDslOrchestration(
        this IServiceCollection services,
        string gatewayAddress)
    {
        return services.AddProcessDslOrchestration(options =>
        {
            options.GatewayAddress = gatewayAddress;
        });
    }
}
