import { ZBClient } from 'zeebe-node';

// Initialize Zeebe client
const zbc = new ZBClient();

/**
 * Payment Validator Job Worker
 * Validates payment information including card number, CVV, and amount
 */
const paymentValidatorWorker = zbc.createWorker({
  taskType: 'payment-validator',
  taskHandler: (job) => {
    console.log(`[Payment Validator] Processing job ${job.key}`);
    console.log(`[Payment Validator] Headers:`, job.customHeaders);
    
    const { amount, cardNumber, cvv } = job.variables;
    const errors: string[] = [];
    
    // Validate amount
    if (!amount || amount <= 0) {
      errors.push('Amount must be greater than 0');
    }
    
    if (amount > 10000) {
      errors.push('Amount exceeds maximum limit of $10,000');
    }
    
    // Validate card number (simple Luhn algorithm check)
    if (!cardNumber || !isValidCardNumber(cardNumber)) {
      errors.push('Invalid card number');
    }
    
    // Validate CVV
    if (!cvv || !/^\d{3,4}$/.test(cvv)) {
      errors.push('Invalid CVV code');
    }
    
    // Check payment method from headers
    const method = job.customHeaders?.method;
    if (method && !['VISA', 'MASTERCARD', 'AMEX'].includes(method)) {
      errors.push(`Unsupported payment method: ${method}`);
    }
    
    const isValid = errors.length === 0;
    
    console.log(`[Payment Validator] Validation result: ${isValid ? 'VALID' : 'INVALID'}`);
    if (!isValid) {
      console.log(`[Payment Validator] Errors:`, errors);
    }
    
    return job.complete({
      isValid,
      validationErrors: errors.length > 0 ? errors : undefined
    });
  }
});

/**
 * Payment Processor Job Worker
 * Processes the actual payment transaction
 */
const paymentProcessorWorker = zbc.createWorker({
  taskType: 'payment-processor',
  taskHandler: async (job) => {
    console.log(`[Payment Processor] Processing job ${job.key}`);
    console.log(`[Payment Processor] Headers:`, job.customHeaders);
    
    const { amount, cardNumber } = job.variables;
    const provider = job.customHeaders?.provider || 'default';
    const currency = job.customHeaders?.currency || 'USD';
    
    try {
      // Simulate payment processing delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Simulate payment processing logic
      const success = Math.random() > 0.1; // 90% success rate
      
      if (!success) {
        throw new Error('Payment processing failed - insufficient funds');
      }
      
      // Generate transaction ID
      const transactionId = `txn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      console.log(`[Payment Processor] Payment successful - Transaction ID: ${transactionId}`);
      console.log(`[Payment Processor] Amount: ${currency} ${amount} via ${provider}`);
      
      return job.complete({
        transactionId,
        status: 'completed'
      });
      
    } catch (error) {
      console.error(`[Payment Processor] Payment failed:`, error);
      
      // For demo purposes, we'll complete with failure status instead of failing the job
      return job.complete({
        transactionId: '',
        status: 'failed'
      });
    }
  }
});

/**
 * Notification Service Job Worker
 * Sends notifications about payment status
 */
const notificationServiceWorker = zbc.createWorker({
  taskType: 'notification-service',
  taskHandler: async (job) => {
    console.log(`[Notification Service] Processing job ${job.key}`);
    
    const { transactionId, customerEmail } = job.variables;
    
    try {
      // Simulate notification sending
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Simulate email sending logic
      console.log(`[Notification Service] Sending notification to ${customerEmail}`);
      console.log(`[Notification Service] Transaction ${transactionId} completed successfully`);
      
      // In a real implementation, you would integrate with an email service like:
      // - SendGrid
      // - AWS SES
      // - Nodemailer with SMTP
      
      console.log(`[Notification Service] Notification sent successfully`);
      
      return job.complete();
      
    } catch (error) {
      console.error(`[Notification Service] Failed to send notification:`, error);
      
      // Throw error to fail the job so it can be retried
      throw new Error('Failed to send notification email');
    }
  }
});

/**
 * Simple Luhn algorithm implementation for card number validation
 */
function isValidCardNumber(cardNumber: string): boolean {
  // Remove spaces and non-digits
  const cleaned = cardNumber.replace(/\D/g, '');
  
  // Check if it's a reasonable length
  if (cleaned.length < 13 || cleaned.length > 19) {
    return false;
  }
  
  // Luhn algorithm
  let sum = 0;
  let isEven = false;
  
  for (let i = cleaned.length - 1; i >= 0; i--) {
    let digit = parseInt(cleaned[i]);
    
    if (isEven) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }
    
    sum += digit;
    isEven = !isEven;
  }
  
  return sum % 10 === 0;
}

/**
 * Graceful shutdown handling
 */
process.on('SIGINT', async () => {
  console.log('\n[Job Workers] Shutting down gracefully...');
  
  await paymentValidatorWorker.close();
  await paymentProcessorWorker.close();
  await notificationServiceWorker.close();
  await zbc.close();
  
  console.log('[Job Workers] All workers stopped');
  process.exit(0);
});

console.log('🚀 Job Workers started successfully!');
console.log('📋 Active workers:');
console.log('   - payment-validator');
console.log('   - payment-processor');
console.log('   - notification-service');
console.log('\nPress Ctrl+C to stop the workers');
