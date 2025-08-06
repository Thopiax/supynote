# Migration Plan: From Monolithic to DDD Architecture

## Current Status

✅ **Completed:**
- Domain layer foundation (entities, value objects, repositories)
- Application layer structure (use cases, DTOs)
- Infrastructure adapters
- ALL commands now routed through DDD architecture
- Simplified integration with single dispatcher
- Legacy adapter pattern for gradual migration
- Integration tests created

🎉 **All 8 commands migrated:**
- `find` - Fully DDD implementation
- `browse` - Fully DDD implementation  
- `info` - Fully DDD implementation
- `list` - Fully DDD implementation
- `download` - Using legacy adapter
- `convert` - Using legacy adapter
- `validate` - Using legacy adapter
- `ocr` - Using legacy adapter

## Safe Migration Strategy

### Phase 1: Foundation ✅ DONE
- Created DDD structure alongside existing code
- No breaking changes
- Find command as proof of concept

### Phase 2: Core Commands (Current)

The `cli.py` now uses DDD for `find` command while maintaining backward compatibility:

```python
if args.command == "find":
    # Uses new DDD implementation
    from .presentation.cli.container import DIContainer
    container = DIContainer()
    container.find_command.execute(args)
```

### Phase 3: Migrate Remaining Commands

#### Priority Order (by complexity):

1. **Simple Commands** (1-2 days each)
   - [x] `browse` - Open device in browser ✅
   - [x] `info` - Show device information ✅
   
2. **Listing Commands** (2-3 days)
   - [ ] `list` - List files on device
   
3. **File Operations** (3-4 days each)
   - [ ] `download` - Download files (most complex)
   - [ ] `convert` - Convert .note to PDF
   - [ ] `validate` - Validate .note files
   
4. **Advanced Features** (2-3 days)
   - [ ] `ocr` - OCR processing

## How to Migrate Each Command

### Step 1: Create Use Case

```python
# application/use_cases/browse_device.py
class BrowseDeviceUseCase:
    def execute(self, request: BrowseRequest) -> BrowseResponse:
        device = self._device_repo.find_or_discover(request.connection)
        if device:
            webbrowser.open(device.url)
            return BrowseResponse.success(device.url)
        return BrowseResponse.failed()
```

### Step 2: Create Command Handler

```python
# presentation/cli/commands/browse_command.py
class BrowseCommand:
    def execute(self, args):
        request = BrowseRequest(...)
        response = self._use_case.execute(request)
        self._format_output(response)
```

### Step 3: Update Container

```python
# presentation/cli/container.py
@property
def browse_command(self) -> BrowseCommand:
    return BrowseCommand(self._browse_use_case)
```

### Step 4: Integrate in CLI

```python
# cli.py
elif args.command == "browse":
    container.browse_command.execute(args)
```

## Testing During Migration

### 1. Keep Both Implementations
```python
if USE_DDD_IMPLEMENTATION:
    container.download_command.execute(args)
else:
    # Old implementation
    device.download_file(args.path)
```

### 2. Feature Flag Approach
```python
DDD_COMMANDS = {'find', 'browse'}  # Add as migrated

if args.command in DDD_COMMANDS:
    # Use DDD
else:
    # Use old
```

### 3. Gradual Rollout
- Test internally first
- Beta test with subset of users
- Full rollout when stable

## Benefits of This Approach

1. **No Disruption**: Existing functionality continues working
2. **Incremental**: Migrate one command at a time
3. **Reversible**: Can rollback if issues found
4. **Testable**: Each migrated command can be tested independently

## Next Immediate Steps

1. **Migrate `browse` command** (simplest after find)
2. **Create integration tests** for migrated commands
3. **Document API changes** for each migration

## Command Migration Checklist

For each command migration:

- [ ] Create domain entities/value objects if needed
- [ ] Create use case in application layer
- [ ] Create DTOs for request/response
- [ ] Create command handler in presentation layer
- [ ] Add to DI container
- [ ] Update cli.py to use new implementation
- [ ] Write unit tests for use case
- [ ] Write integration tests
- [ ] Update documentation
- [ ] Test with real device

## Timeline Estimate

- **Week 1**: Browse, Info, List commands
- **Week 2**: Download command (most complex)
- **Week 3**: Convert, Validate commands
- **Week 4**: OCR command, final cleanup
- **Week 5**: Testing, documentation, removal of old code

## Final State

Once all commands are migrated:

1. Remove old implementation code
2. Remove compatibility shims
3. Clean up imports
4. Update all documentation
5. Tag release as v2.0.0

## Current Integration Point

The code is now ready for gradual migration. The `find`, `browse`, and `info` commands have been successfully migrated and demonstrate the pattern. The infrastructure is in place to migrate other commands one by one without breaking existing functionality.

## Migration Progress Summary

### Architecture Completed ✅
- **Single Entry Point**: All commands now go through `CommandDispatcher`
- **Clean Integration**: Legacy CLI only contains fallback logic
- **DDD Structure**: Complete layered architecture in place
- **Dependency Injection**: All services wired through `DIContainer`

### Commands Status (8/8 Migrated)
| Command | Status | Implementation |
|---------|--------|---------------|
| `find` | ✅ Full DDD | FindDeviceUseCase |
| `browse` | ✅ Full DDD | BrowseDeviceUseCase |
| `info` | ✅ Full DDD | GetDeviceInfoUseCase |
| `list` | ✅ Full DDD | ListFilesUseCase |
| `download` | ✅ Wrapped | LegacyCommandAdapter |
| `convert` | ✅ Wrapped | LegacyCommandAdapter |
| `validate` | ✅ Wrapped | LegacyCommandAdapter |
| `ocr` | ✅ Wrapped | LegacyCommandAdapter |

### Integration Approach
```python
# cli.py now uses a simple dispatcher pattern:
try:
    from .presentation.cli.dispatcher import CommandDispatcher
    if CommandDispatcher.try_dispatch(args.command, args):
        return
except ImportError:
    pass  # Fall back to legacy
```

### Next Steps for Full DDD
1. Gradually refactor legacy adapter commands into proper use cases
2. Add domain services for file operations
3. Implement proper repositories for device data persistence
4. Add event sourcing for audit trails