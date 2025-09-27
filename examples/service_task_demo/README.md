# Service Task Demo - Job Workers

This directory contains TypeScript job workers that implement the service tasks defined in the `service_task_demo.bpm` ProcessDSL file.

## Overview

The demo implements a payment processing workflow with three service tasks:

1. **payment-validator** - Validates payment information (amount, card number, CVV)
2. **payment-processor** - Processes the actual payment transaction
3. **notification-service** - Sends notifications about payment completion

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Payment Request │───▶│ Validate Payment │───▶│ Payment Valid?  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                    ┌────▼────┐
                                                    │ Process │
                                                    │ Payment │
                                                    └────┬────┘
                                                         │
                                                    ┌────▼────┐
                                                    │  Send   │
                                                    │Notification│
                                                    └────┬────┘
                                                         │
                                                    ┌────▼────┐
                                                    │Payment  │
                                                    │Completed│
                                                    └─────────┘
```

## Prerequisites

- Node.js 16+ 
- Camunda Zeebe cluster (local or cloud)
- TypeScript (for development)

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure Zeebe connection:**
   
   The job workers use the default Zeebe client configuration. You can customize the connection by setting environment variables:
   
   ```bash
   # For Camunda Cloud
   export ZEEBE_ADDRESS=your-cluster-id.region.zeebe.camunda.io:443
   export ZEEBE_CLIENT_ID=your-client-id
   export ZEEBE_CLIENT_SECRET=your-client-secret
   
   # For local Zeebe
   export ZEEBE_ADDRESS=localhost:26500
   ```

3. **Build the TypeScript code:**
   ```bash
   npm run build
   ```

## Running the Job Workers

### Development Mode (with hot reload):
```bash
npm run dev
```

### Production Mode:
```bash
npm start
```

### Watch Mode (rebuilds on changes):
```bash
npm run watch
```

## Job Worker Details

### Payment Validator Worker
- **Task Type:** `payment-validator`
- **Input Variables:** `amount`, `cardNumber`, `cvv`
- **Output Variables:** `isValid`, `validationErrors`
- **Headers Used:** `method`, `timeout`
- **Validation Rules:**
  - Amount must be > 0 and ≤ $10,000
  - Card number validated using Luhn algorithm
  - CVV must be 3-4 digits
  - Payment method must be VISA, MASTERCARD, or AMEX

### Payment Processor Worker
- **Task Type:** `payment-processor`
- **Input Variables:** `amount`, `cardNumber`
- **Output Variables:** `transactionId`, `status`
- **Headers Used:** `provider`, `currency`
- **Features:**
  - Simulates payment processing with 2-second delay
  - 90% success rate for demo purposes
  - Generates unique transaction IDs
  - Supports different payment providers

### Notification Service Worker
- **Task Type:** `notification-service`
- **Input Variables:** `transactionId`, `customerEmail`
- **Output Variables:** None
- **Features:**
  - Simulates email notification sending
  - 1-second processing delay
  - Ready for integration with email services (SendGrid, AWS SES, etc.)

## Testing the Workflow

1. **Deploy the BPMN process to Zeebe:**
   ```bash
   # Using zbctl (Zeebe CLI)
   zbctl deploy service_task_demo.bpmn
   ```

2. **Start the job workers:**
   ```bash
   npm run dev
   ```

3. **Create a process instance:**
   ```bash
   zbctl create instance payment-process --variables '{
     "amount": 99.99,
     "cardNumber": "4532015112830366",
     "cvv": "123",
     "customerEmail": "customer@example.com"
   }'
   ```

## Example Process Variables

### Valid Payment:
```json
{
  "amount": 99.99,
  "cardNumber": "4532015112830366",
  "cvv": "123",
  "customerEmail": "customer@example.com"
}
```

### Invalid Payment (will fail validation):
```json
{
  "amount": -50,
  "cardNumber": "1234567890123456",
  "cvv": "12",
  "customerEmail": "customer@example.com"
}
```

## Monitoring

The job workers provide detailed console logging:

```
🚀 Job Workers started successfully!
📋 Active workers:
   - payment-validator
   - payment-processor
   - notification-service

[Payment Validator] Processing job 123456789
[Payment Validator] Headers: { method: 'VISA', timeout: '30s' }
[Payment Validator] Validation result: VALID
[Payment Processor] Processing job 123456790
[Payment Processor] Payment successful - Transaction ID: txn_1640995200000_abc123def
[Notification Service] Processing job 123456791
[Notification Service] Sending notification to customer@example.com
[Notification Service] Notification sent successfully
```

## Error Handling

- **Payment Validator:** Returns validation errors in the `validationErrors` array
- **Payment Processor:** Completes with `status: 'failed'` on processing errors
- **Notification Service:** Fails the job to trigger retries if notification sending fails

## Extending the Workers

To add new functionality:

1. **Add new input/output variable types** in the TypeScript interfaces
2. **Implement additional validation logic** in the payment validator
3. **Integrate with real payment providers** (Stripe, PayPal, etc.)
4. **Add email service integration** (SendGrid, AWS SES, etc.)
5. **Add monitoring and metrics** collection

## Troubleshooting

### Common Issues:

1. **Connection refused:** Ensure Zeebe is running and accessible
2. **Authentication failed:** Check your Camunda Cloud credentials
3. **Jobs not being picked up:** Verify task types match exactly between BPMN and workers
4. **TypeScript compilation errors:** Run `npm run build` to check for syntax issues

### Debug Mode:
Set the environment variable for more detailed logging:
```bash
export ZEEBE_LOG_LEVEL=debug
npm run dev
```

## License

MIT License - See the main ProcessDSL project for details.
