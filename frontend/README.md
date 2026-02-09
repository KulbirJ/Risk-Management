# Compliance Platform Frontend

Next.js 14 frontend for the Compliance Platform threat risk assessment application.

## Features

- 🔐 AWS Cognito authentication with JWT tokens
- 📊 Dashboard with risk metrics and statistics
- 📝 Assessment management (CRUD operations)
- ⚠️ Threat tracking with severity calculations
- 📁 Evidence management with S3 file uploads
- 💡 Recommendations tracking
- 🎯 Risk register with acceptance workflow
- 📜 Complete audit log viewer
- 🎨 Modern UI with Tailwind CSS
- 📱 Responsive design

## Prerequisites

- Node.js 18+ and npm
- Running backend API (see backend README)

## Getting Started

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.local.example .env.local
   ```

   Edit `.env.local` with your settings:
   - For **local development** with mock auth, leave Cognito values empty
   - For **production** with Cognito, set your User Pool ID and Client ID

3. **Run development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:**
   ```
   http://localhost:3000
   ```

## Configuration

### Mock Authentication (Local Development)

```env
NEXT_PUBLIC_USE_MOCK_AUTH=true
NEXT_PUBLIC_MOCK_TENANT_ID=67636bd3-9846-4bde-806f-aea369fc9457
NEXT_PUBLIC_MOCK_USER_ID=0bc9d6a9-f342-452e-9297-ee33f44d4f84
```

### AWS Cognito (Production)

```env
NEXT_PUBLIC_AWS_REGION=ca-west-1
NEXT_PUBLIC_COGNITO_USER_POOL_ID=your-user-pool-id
NEXT_PUBLIC_COGNITO_CLIENT_ID=your-client-id
NEXT_PUBLIC_USE_MOCK_AUTH=false
```

## Project Structure

```
frontend/
├── app/                      # Next.js 14 App Router
│   ├── layout.tsx           # Root layout with auth
│   ├── page.tsx             # Dashboard
│   ├── assessments/         # Assessment pages
│   ├── active-risks/        # Risk register
│   └── audit-logs/          # Audit log viewer
├── components/              # Reusable UI components
│   ├── AuthProvider.tsx     # Cognito auth wrapper
│   ├── Layout.tsx           # Main layout with sidebar
│   ├── Button.tsx           # Button component
│   ├── Badge.tsx            # Status/severity badges
│   └── ...
├── lib/                     # Utilities and configurations
│   ├── api-client.ts        # API client with JWT injection
│   ├── amplify-config.ts    # AWS Amplify setup
│   └── types.ts             # TypeScript types
└── public/                  # Static assets
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## API Integration

The frontend uses a centralized API client (`lib/api-client.ts`) that:

- Automatically injects JWT tokens from Cognito
- Falls back to header-based auth for local development
- Handles authentication errors
- Provides type-safe methods for all backend endpoints

## Authentication Flow

### Mock Mode (Development)
1. No login required
2. Uses X-Tenant-Id and X-User-Id headers
3. Perfect for local testing

### Cognito Mode (Production)
1. User signs in via Amplify UI
2. JWT token obtained from Cognito
3. Token automatically included in all API requests
4. Backend validates token and auto-provisions user

## Key Features

### Assessments
- Create, view, edit, and delete assessments
- Track status (draft, in_progress, completed, archived)
- Set risk appetite and target dates
- View associated threats and recommendations

### Risk Register
- View all active risks
- Filter by status and severity
- Accept risks with rationale
- Track risk ownership and review dates

### Audit Logs
- Complete change history
- Filter by action, entity type, and actor
- View old/new values for updates
- Immutable audit trail

## Deployment

### Vercel (Recommended)
```bash
npm run build
vercel deploy
```

### Docker
```bash
docker build -t compliance-frontend .
docker run -p 3000:3000 compliance-frontend
```

## Troubleshooting

**CORS errors:**
- Ensure backend has correct CORS_ORIGINS in .env
- Check that API_URL is correct in frontend .env.local

**Authentication issues:**
- Verify Cognito User Pool and Client IDs
- Check that backend has matching Cognito configuration
- For mock auth, verify tenant and user IDs exist in database

**Build errors:**
- Clear `.next` folder: `rm -rf .next`
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

## License

MIT
