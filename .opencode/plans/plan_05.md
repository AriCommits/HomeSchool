# Improvement Plan: Multiple ChromaDB Databases Support

## Problem Statement
Currently, the Homeschool system only supports a single ChromaDB collection. Users who want to separate different types of documents (e.g., graduate school applications vs. homework) have no built-in way to maintain separate vector databases without manually managing multiple instances, which creates operational overhead.

## Proposed Solution
Implement support for multiple logical databases using a single ChromaDB instance with multiple collections. Each "database" will be represented as a ChromaDB collection within the same instance, with configuration mapping each database to specific vault subpaths and collection names.

## Approach Overview
- **Single ChromaDB Instance**: Run one ChromaDB service with instance-level authentication
- **Multiple Collections**: Each logical database maps to a separate ChromaDB collection
- **Configuration-Driven**: Define databases in config.yaml with vault subpaths and collection names
- **CLI Selection**: Specify target database via `--database` argument
- **Default Behavior**: Maintain backward compatibility with existing "default" database

## Detailed Changes

### 1. Configuration Structure (`config.yaml`)
```yaml
# Existing sections remain unchanged...
chromadb:
  distance_metric: "cosine"
  auth_token: "your_generated_token_here"  # Instance-level token

# New databases section
databases:
  default:  # Used when no database specified
    vault_subpath: ""  # Sync entire vault
    collection: "homeschool"
  essay:
    vault_subpath: "essays"  # Sync only essays subdirectory
    collection: "essay_collection"
  homework:
    vault_subpath: "homework"
    collection: "homework_collection"
```

### 2. CLI Modifications (`homeschool/cli.py`)
- [x] Add `--database` argument to the `sync` subcommand
- [x] Default to "default" database when not specified
- [x] Pass database name to sync worker via `SYNC_DATABASE` environment variable
- [x] Update help text and examples

### 3. Docker-Compose Updates (`.docker/compose.yaml`)
- [x] Mount the complete config.yaml file into the sync_worker container
- [x] Pass database name via environment variable: `SYNC_DATABASE=${SYNC_DATABASE:-default}`
- [x] Keep existing volume mounts for vault and model store (they remain read-only)
- [x] Ensure config.yaml is accessible at a known path inside the container

### 4. Sync Worker Updates (`homeschool/sync.py`)
- [x] Load configuration from the mounted config.yaml
- [x] Read `SYNC_DATABASE` environment variable (defaults to "default")
- [x] Validate database exists in configuration
- [x] Calculate sync directory: `vault_path / database_config.vault_subpath`
- [x] Use `database_config.collection` as the ChromaDB collection name
- [x] Initialize ChromaDB client with instance auth token from chromadb section
- [x] Get or create the specified collection
- [x] Process files from the calculated sync directory (basic file discovery and logging implemented)

### 5. Security Considerations
- [x] Single auth token for the ChromaDB instance (reasonable trade-off for simplicity)
- [x] Collections are logically isolated within the instance
- [x] No additional credential management overhead for multiple databases
- [x] Vault paths remain read-only mounts as before

### 6. Default Behavior & Backward Compatibility
- [x] When no `--database` flag is provided, system uses "default" database
- [x] Existing configurations without databases section will continue working
- [x] Default database configuration mimics current behavior (full vault sync to "homeschool" collection)
- [x] No breaking changes to existing user setups

## Implementation Order
- [x] 1. Update configuration schema and validation in `config.py`
- [x] 2. Modify CLI to accept and handle `--database` argument
- [x] 3. Update docker-compose to mount config and pass database variable
- [x] 4. Enhance sync worker to load database-specific configuration
- [x] 5. Test with multiple database scenarios
- [x] 6. Update documentation and examples

## Benefits
- [x] Zero operational overhead for adding new logical databases
- [x] Clean separation of different document types
- [x] Maintains existing workflow for single-database use cases
- [x] Efficient resource usage (single ChromaDB instance)
- [x] Simple CLI interface for database selection

## Example Usage
```bash
# Sync to default database (existing behavior)
homeschool sync

# Sync essays to essay database
homeschool sync --database essay

# Sync homework to homework database
homeschool sync --database homework
```