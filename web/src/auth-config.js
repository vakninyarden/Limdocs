import { Amplify } from 'aws-amplify'

const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID ?? ''
const userPoolClientId = import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID ?? ''

// #region agent log
fetch('http://127.0.0.1:7342/ingest/c12bd9e5-3c3e-438c-8677-68452c921326',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'4bfbe0'},body:JSON.stringify({sessionId:'4bfbe0',runId:'signup-debug-1',hypothesisId:'H1',location:'src/auth-config.js:6',message:'Amplify config bootstrap',data:{hasUserPoolId:Boolean(userPoolId),hasUserPoolClientId:Boolean(userPoolClientId),userPoolIdPrefix:userPoolId.slice(0,10),clientIdLength:userPoolClientId.length},timestamp:Date.now()})}).catch(()=>{});
// #endregion

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId,
      userPoolClientId,
      loginWith: {
        username: true,
        email: true,
      },
    },
  },
})
