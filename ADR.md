# Architecture Decision Records (ADRs)

## 1. Choice of Backend Framework - FastAPI

**Date**: August 24, 2026  
**Status**: Accepted

### Context
We needed a modern, high-performance Python web framework for building our API that supports asynchronous operations, automatic API documentation, and easy integration with machine learning services.

### Decision
We chose FastAPI as our backend framework because:
- Native support for async/await operations
- Automatic generation of interactive API documentation (Swagger/OpenAPI)
- Built-in data validation with Pydantic
- Excellent performance comparable to Node.js and Go
- Native WebSocket support for real-time updates
- Easy integration with SQLAlchemy/SQLModel for ORM
- Growing community and excellent documentation

### Consequences
- Enables real-time WebSocket communication for live recommendation updates
- Provides automatic API documentation at `/docs` and `/redoc`
- Built-in data validation reduces bugs and improves API reliability
- Asynchronous operations allow handling many concurrent requests efficiently

## 2. Choice of Frontend Framework - React with Vite

**Date**: August 24, 2026  
## 3. Database Choice - SQLite with SQLModel

**Date**: August 24, 2026  
**Status**: Accepted

### Context
We needed a database solution that would be easy to set up for development while being scalable for potential future production deployment.

### Decision
We chose SQLite with SQLModel because:
- SQLite requires zero configuration and is file-based
- Perfect for development and easy to version control
- SQLModel provides a unified interface for both SQL and NoSQL databases
- Built-in integration with Pydantic for data validation
- Can easily migrate to PostgreSQL for production with minimal code changes
- Supports both synchronous and asynchronous operations

### Consequences
- Simple development setup with no external database dependencies
- Easy to reset and reseed data during development
- Type-safe database operations reduce errors
- Smooth migration path to production databases
## 5. Real-time Communication - WebSockets

**Date**: August 24, 2026  
**Status**: Accepted

### Context
We needed to push AI recommendations to connected clients in real-time as soon as they become available, rather than requiring clients to poll for updates.

### Decision
We implemented WebSocket communication because:
- Bidirectional communication between client and server
- Persistent connections reduce overhead
- Native support in FastAPI
- Wide browser support
- Efficient for real-time updates

### Consequences
- Instant delivery of recommendations to all connected clients
- Reduced network traffic compared to polling
- Enhanced user experience with immediate feedback
## 7. Recommendation System Design - Event-Driven Triggers

**Date**: August 24, 2026  
**Status**: Accepted

### Context
We needed to determine when to trigger AI recommendations based on business rules.

### Decision
We implemented event-driven triggers based on:
- Stock level falling below reorder threshold
- Demand velocity exceeding configured threshold
- Status changes in products

### Consequences
- Recommendations generated only when meaningful business events occur
- Reduces unnecessary AI API calls
- Ensures recommendations are contextually relevant
- Provides clear audit trail of recommendation triggers

## 8. Configuration Management - Environment Variables

**Date**: August 24, 2026  
**Status**: Accepted

### Context
We needed to manage configuration parameters that vary between environments (development, staging, production) and contain sensitive information.

### Decision
We use environment variables for configuration:
- LLM API keys stored securely
- Database URLs configurable per environment
- Feature flags for optional functionality
- Pydantic BaseSettings for validation and type safety

### Consequences
- Secure handling of sensitive credentials
- Easy environment-specific configuration
- Type-safe configuration access
- Standard approach compatible with deployment platforms
- Slightly increased complexity in connection management

## 6. Data Modeling - Separate Product and Order Entities

**Date**: August 24, 2026  
**Status**: Accepted

### Context
We needed to represent both static product information and dynamic transaction data in our system.

### Decision
We separated data into Product and Order entities:
- Product entity contains static information with derived metrics
- Order entity tracks transaction history
- Demand velocity calculated from order frequency and quantity
- Stock levels updated in real-time with each order

### Consequences
- Normalized data structure reduces redundancy
- Clear separation of concerns between product catalog and transaction data
- Enables historical analysis of sales patterns
- Supports accurate demand velocity calculations

## 4. AI Integration Approach - Asynchronous Background Processing

**Date**: August 24, 2026  
**Status**: Accepted

### Context
Our AI-powered recommendations rely on an external LLM API that can have variable response times. We needed to ensure that API responses aren't blocked by these potentially slow operations.

### Decision
We implemented AI integration using asynchronous background processing:
- FastAPI background tasks for non-blocking AI calls
- WebSocket notifications for pushing recommendations to clients
- Error handling for failed AI requests
- Caching mechanisms for repeated requests

### Consequences
- Immediate API responses improve user experience
- Real-time updates through WebSockets provide instant feedback
- System resilience against slow or failing AI services
- Scalable architecture that can handle multiple concurrent AI requests
**Status**: Accepted

### Context
We needed a modern frontend framework that provides a responsive user interface for displaying real-time inventory data and AI recommendations.

### Decision
We chose React with Vite because:
- React provides a component-based architecture for building reusable UI elements
- Vite offers extremely fast hot module replacement (HMR) and build times
- Excellent ecosystem and community support
- Strong TypeScript support
- Efficient rendering with virtual DOM
- Easy WebSocket integration for real-time updates

### Consequences
- Fast development experience with instant feedback
- Component-based architecture promotes reusability and maintainability
- Efficient handling of real-time data updates through React hooks
- Built-in development server with hot reloading