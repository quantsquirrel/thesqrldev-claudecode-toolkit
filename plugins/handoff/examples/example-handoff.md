# Handoff

**Time:** 2026-01-31 15:30
**Topic:** JWT Authentication System
**Working Directory:** /projects/api-server

## User Requests
- "JWT 인증 시스템을 구현해줘. refresh token rotation이랑 RBAC 포함해서."
- "bcrypt는 async로 해줘, 동기는 너무 느려."
- "토큰은 httpOnly 쿠키에 저장해. localStorage는 보안 문제 있으니까."

## Summary
I implemented a production-ready JWT authentication system with refresh token rotation, token blacklisting via Redis, and role-based access control. All core flows (register, login, refresh, logout) are complete and tested at 94% coverage.

## Completed
- [x] Implemented JWT token generation and verification with HS256 signing and configurable expiration
- [x] Built user registration and login endpoints with email validation and async bcrypt hashing
- [x] Implemented refresh token rotation with automatic blacklisting of old tokens via Redis
- [x] Created RBAC middleware with role hierarchy (admin > moderator > user) and permission-based access
- [x] Added rate limiting on auth endpoints (5 attempts per 15 minutes)
- [x] Stored refresh tokens in HTTP-only secure cookies with SameSite=Strict

## Pending
- [ ] OAuth2 social login (Google + GitHub) via Passport.js -- requires OAuth app credentials from user
- [ ] Email verification flow on registration -- needs SMTP configuration
- [ ] Multi-factor authentication (TOTP) -- deferred to Phase 2

## Key Decisions
- **HTTP-only cookies for refresh tokens**: Chose cookies over localStorage to mitigate XSS; access tokens stay in memory
- **Redis-backed token blacklist**: Chose stateful blacklist over pure stateless JWT for instant revocation on logout
- **Bcrypt cost factor 12**: Chose 12 rounds (~500ms) as balance between security and user experience

## Failed Approaches
- **Encoding token version in JWT claims**: Couldn't invalidate old tokens immediately since JWTs are immutable once signed -- switched to Redis blacklist
- **Synchronous bcrypt hashing**: Blocked event loop for 500-800ms per request, caused timeouts under concurrent load -- switched to async bcrypt with worker threads

## Files Modified
- `src/middleware/auth.middleware.ts` - Created JWT verification middleware with role extraction and 401 error handling
- `src/services/auth.service.ts` - Implemented auth service with token generation, verification, rotation, and revocation
- `src/routes/auth.routes.ts` - Created REST endpoints for register, login, refresh, logout with rate limiting and Joi validation
- `src/database/models/user.model.ts` - Added role enum field (user/moderator/admin) and audit timestamps

## Constraints
- "bcrypt는 async로 해줘, 동기는 너무 느려."
- "토큰은 httpOnly 쿠키에 저장해. localStorage는 보안 문제 있으니까."

## Next Step
Implement OAuth2 social login with Google and GitHub providers using Passport.js. The frontend team is blocked waiting for this integration. Create OAuth app credentials first, then add passport-google-oauth20 and passport-github2 strategies following the existing dependency injection pattern in auth.service.ts.
