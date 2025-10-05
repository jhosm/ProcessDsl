import { ZBClient } from 'zeebe-node';
import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

/**
 * Process Entity Validator Job Worker
 * Validates data against OpenAPI schemas for processEntity elements
 */
export class ProcessEntityValidator {
  private zbc: ZBClient;
  private worker: any;

  constructor(zbc: ZBClient) {
    this.zbc = zbc;
    this.worker = null;
  }

  /**
   * Start the process entity validator worker
   */
  start() {
    this.worker = this.zbc.createWorker({
      taskType: 'process-entity-validator',
      taskHandler: (job) => {
        console.log(`[Process Entity Validator] Processing job ${job.key}`);
        console.log(`[Process Entity Validator] Headers:`, job.customHeaders);
        console.log(`[Process Entity Validator] Job variables:`, job.variables);
        
        const { processEntity } = job.variables;
        const entityModel = job.customHeaders?.entityModel;
        const entityName = job.customHeaders?.entityName;
        
        console.log(`[Process Entity Validator] processEntity data:`, processEntity);
        console.log(`[Process Entity Validator] processEntity type:`, typeof processEntity);
        
        // Check if processEntity data exists and is an object
        if (!processEntity || typeof processEntity !== 'object') {
          console.error(`[Process Entity Validator] Invalid processEntity data. Expected object, got:`, typeof processEntity);
          return job.complete({
            validationResult: {
              isValid: false,
              errors: [`Invalid processEntity data. Expected object, got: ${typeof processEntity}`],
              entityName: entityName || 'unknown',
              entityModel: entityModel || 'unknown'
            }
          });
        }
        
        if (!entityName) {
          console.error(`[Process Entity Validator] Missing required header: entityName`);
          return job.complete({
            validationResult: {
              isValid: false,
              errors: ['Missing entityName in task headers'],
              entityName: 'unknown',
              entityModel: entityModel || 'unknown'
            }
          });
        }
        
        // Determine the path to the OpenAPI contracts folder next to the built JS file
        // Note: __dirname will point to the compiled JS directory at runtime
        const contractsBaseDir = path.resolve(__dirname, 'openAPI_contracts');
        
        if (!entityModel || typeof entityModel !== 'string') {
          console.error(`[Process Entity Validator] Missing required header: entityModel`);
          return job.complete({
            validationResult: {
              isValid: false,
              errors: ['Missing entityModel in task headers'],
              entityName,
              entityModel: 'unknown'
            }
          });
        }
        
        // Normalize the model path (remove any leading slashes so it's safely joined under contractsBaseDir)
        const normalizedModel = entityModel.replace(/^\/+/, '');
        const modelPath = path.resolve(contractsBaseDir, normalizedModel);
        
        if (!fs.existsSync(modelPath)) {
          console.error(`[Process Entity Validator] OpenAPI model not found at: ${modelPath}`);
          return job.complete({
            validationResult: {
              isValid: false,
              errors: [`OpenAPI model not found at: ${modelPath}`],
              entityName,
              entityModel
            }
          });
        }
        
        try {
          // Load OpenAPI spec from file (supports .yaml/.yml/.json)
          const ext = path.extname(modelPath).toLowerCase();
          const raw = fs.readFileSync(modelPath, 'utf8');
          let openApiSpec: any;
          if (ext === '.yaml' || ext === '.yml') {
            openApiSpec = yaml.load(raw);
          } else if (ext === '.json') {
            openApiSpec = JSON.parse(raw);
          } else {
            // Try YAML first, then JSON as a fallback
            try {
              openApiSpec = yaml.load(raw);
            } catch (e) {
              openApiSpec = JSON.parse(raw);
            }
          }
          
          // Extract entity schema from OpenAPI spec
          const entitySchema = openApiSpec?.components?.schemas?.[entityName];
          if (!entitySchema) {
            throw new Error(`Entity '${entityName}' not found in OpenAPI schema`);
          }
          
          // Initialize AJV validator with OpenAPI-compatible settings
          const ajv = new Ajv({ 
            allErrors: true,
            strict: false,  // Disable strict mode to allow OpenAPI keywords
            validateFormats: true
          });
          addFormats(ajv);
          
          // Add the full OpenAPI spec to AJV for $ref resolution
          if (openApiSpec.components?.schemas) {
            for (const [schemaName, schema] of Object.entries(openApiSpec.components.schemas)) {
              ajv.addSchema(schema as any, `#/components/schemas/${schemaName}`);
            }
          }
          
          // Validate the processEntity data
          const validate = ajv.compile(entitySchema as any);
          const isValid = validate(processEntity);
          
          let errors: string[] = [];
          if (!isValid && validate.errors) {
            errors = validate.errors.map((error: any) => {
              const path = error.instancePath || error.schemaPath;
              return `${path}: ${error.message}`;
            });
          }
          
          console.log(`[Process Entity Validator] Validation result: ${isValid ? 'VALID' : 'INVALID'}`);
          if (!isValid) {
            console.log(`[Process Entity Validator] Errors:`, errors);
          }
          
          return job.complete({
            validationResult: {
              isValid,
              errors,
              entityName,
              entityModel: entityModel || 'unknown'
            }
          });
          
        } catch (error: any) {
          console.error(`[Process Entity Validator] Error:`, error);
          
          return job.complete({
            validationResult: {
              isValid: false,
              errors: [`Validation error: ${error.message}`],
              entityName,
              entityModel: entityModel || 'unknown'
            }
          });
        }
      }
    });

    console.log('✅ Process Entity Validator worker started');
    return this.worker;
  }

  /**
   * Stop the worker
   */
  async stop() {
    if (this.worker) {
      await this.worker.close();
      console.log('🛑 Process Entity Validator worker stopped');
    }
  }
}

