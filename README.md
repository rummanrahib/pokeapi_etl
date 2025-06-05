# Pokemon ETL (PokéPipeline)

A robust ETL (Extract, Transform, Load) pipeline that fetches Pokemon data from the PokéAPI, transforms it into a structured format, and stores it in a PostgreSQL database. Built with Django and Django REST Framework.

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Setup and Installation](#setup-and-installation)
- [Admin Interface](#admin-interface)
- [Design Choices](#design-choices)
- [Future Enhancements](#future-enhancements)

## Project Overview

This project implements a data pipeline that:
- Extracts Pokemon data from [PokeAPI](https://pokeapi.co/)
- Transforms the nested API responses into a normalized structure
- Loads the data into a PostgreSQL database
- Provides a comprehensive Django [admin](http://localhost:8000/admin/) interface to manage the data
- (Future) Integrates REST and GraphQL API endpoints to access the stored data
- (Future) Includes a NextJS frontend for data visualization

## Architecture

### Database Schema
The project uses a normalized database schema with the following models:

1. **Pokemon**
   - Core Pokemon attributes (id, name, height, weight, etc.)
   - Base stats (hp, attack, defense, sp. attack, sp. defense, speed)
   - Many-to-many relationships with Types, Abilities, and Moves
   - Foreign key to PokemonSpecies

2. **PokemonSpecies**
   - Species-specific information (genus, description)
   - Evolution chain relationships
   - Base happiness and capture rate

3. **Type**
   - Pokemon types (fire, water, etc.)
   - Type effectiveness relationships

4. **Ability**
   - Pokemon abilities
   - Effect descriptions
   - Is hidden ability flag

5. **Move**
   - Move details (name, power, accuracy)
   - Damage class (physical, special, status)
   - Move type and effects

6. **PokemonMove**
   - Junction table for Pokemon-Move relationship
   - Learn method (level-up, egg, tutor, machine)
   - Level learned at (for level-up moves)

### ETL Pipeline
The ETL process is organized into three main components:

1. **Extractor** (`extractors.py`)
   - Handles API communication with PokeAPI
   - Implements retry logic with exponential backoff
   - Rate limiting to respect API guidelines
   - Concurrent fetching with safety limits
   - Error handling and logging

2. **Transformer** (`transformers.py`)
   - Transforms raw API responses into model-ready data
   - Normalizes nested JSON structures
   - Validates data integrity and relationships
   - Handles missing or invalid data gracefully

3. **Loader** (`loaders.py`)
   - Manages database operations efficiently
   - Handles model relationships and constraints
   - Uses bulk operations where possible
   - Ensures data consistency and atomicity

## Setup and Installation

### Prerequisites
- Docker and Docker Compose
- Git

### Clone and Setup
```bash
# Clone the repository
git clone https://github.com/rummanrahib/pokeapi_etl.git

cd pokeapi_etl

# Create environment file
cd backend
touch .env

# Edit the .env file
nano .env

# Add the following variables
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DB_NAME=pokemon_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

### Running the Project
```bash
# Build and start the services in detached mode
docker-compose build
docker-compose up -d

# Check if services are running
docker-compose ps

# Run migrations
docker-compose exec backend python manage.py migrate

# Create a superuser (creates admin1, admin2, etc. if username exists)
docker-compose exec backend python manage.py createsuperuser_default \
    --username=myuser \
    --email=myuser@example.com \
    --password=mypassword

# Load Pokemon data (default: 20 Pokemon, 3 moves each -- takes around 10s)
docker-compose exec backend python manage.py sync_pokemon

# For more Pokemon (adjust limit as needed -- will take longer):
docker-compose exec backend python manage.py sync_pokemon --limit 30

# To stop the services
docker-compose down

# To stop and remove all data (including database)
docker-compose down -v
```

### Troubleshooting Docker Setup

If you encounter any issues:

1. **Services not starting properly:**
   ```bash
   # Check service logs
   docker-compose logs

   # Check specific service logs
   docker-compose logs backend
   docker-compose logs db
   ```

2. **Database connection issues:**
   ```bash
   # Rebuild and restart services
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

## Admin Interface

Access the Django admin interface at `http://localhost:8000/admin/` with your superuser credentials with username: `myuser` and password: `mypassword`.

### Available Management Interfaces

1. **Pokemon Management**
   - Full CRUD operations for Pokemon entities
   - Search: By name, Pokedex ID
   - Filters: Types, Generation, Stats range
   - Sorting: Pokedex ID, Name, Stats
   - Batch actions: Update types, Delete
   - 100 Pokemon per page with pagination

2. **Move Management**
   - Complete move database management
   - Filters: Move type, Damage class, Power range
   - Search: Move name, Effect
   - Sorting: Name, Power, Accuracy
   - Batch actions available

3. **Pokemon-Move Relationships**
   - Manage move learning methods
   - Filters: Learn method, Level requirement
   - Search: Pokemon or move name
   - Bulk assign/remove moves
   - Sort by level requirement

4. **Additional Model Management**
   - Types: Manage Pokemon types and relationships
   - Abilities: Configure Pokemon abilities
   - Evolution Chains: Manage evolution relationships
   - Species: Handle species-specific data

## Design Choices

### Data Transformation
1. **Normalized Structure**
   - Optimized database schema
   - Reduced data redundancy
   - Efficient querying capabilities
   - Maintainable data relationships

2. **Selective Data Loading**
   - Configurable Pokemon limit
   - Adjustable moves per Pokemon
   - Focus on essential attributes
   - Optimized memory usage

3. **Performance Strategy**
   - No redundant API calls
   - Efficient database operations
   - Proper indexing
   - Cached relationships

### Performance Optimizations
1. **Batch Processing**
   - Configurable batch sizes
   - Bulk database operations
   - Memory-efficient processing
   - Progress tracking

2. **API Interaction**
   - Respectful rate limiting
   - Exponential backoff
   - Connection pooling
   - Error recovery

3. **Error Handling**
   - Comprehensive logging
   - Graceful failure recovery
   - Data validation
   - Transaction management

## Future Enhancements

1. **Frontend Development**
   - NextJS frontend with TypeScript
   - Interactive Pokemon browser
   - Advanced search and filters
   - Data visualization dashboards
   - Responsive design

2. **API Enhancements**
   - RESTful API endpoints
   - GraphQL integration
   - Rate limiting
   - Response caching
   - API documentation

3. **Pipeline Improvements**
   - Async data fetching
   - More Pokemon attributes
   - Enhanced error reporting and logging

4. **Admin Interface**
   - Custom bulk actions
   - Advanced filters
   - Data export (CSV, JSON)
   - Import functionality
