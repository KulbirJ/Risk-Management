// Phase 0: Mock Auth - Amplify not configured yet
// In Phase 1+,configure AWS Amplify for Cognito authentication

export const isCognitoEnabled = process.env.NEXT_PUBLIC_USE_MOCK_AUTH !== 'true';

// Placeholder for future Amplify configuration
export const amplifyConfig = {
  Auth: {
    region: process.env.NEXT_PUBLIC_AWS_REGION || 'ca-west-1',
    userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID || '',
    userPoolClientId: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID || '',
  },
  API: {
    endpoint: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
};

export default amplifyConfig;
