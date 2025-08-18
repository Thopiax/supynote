# Domain-Driven Design Refactoring

## Overview

This document describes the Domain-Driven Design (DDD) refactoring of the Supynote CLI application. The refactoring transforms the monolithic 692-line `cli.py` file into a clean, layered architecture following DDD principles.

## Completed Work

### ✅ Phase 1: Domain Layer Structure

Created the foundation of the domain model:

```
supynote/
├── domain/
│   ├── shared/
│   │   ├── base_entity.py         # Entity and AggregateRoot base classes
│   │   └── base_value_object.py   # ValueObject base classes
│   ├── note_management/
│   │   ├── entities/
│   │   │   └── note.py            # Note aggregate root
│   │   ├── value_objects/
│   │   │   ├── note_id.py         # NoteId value object
│   │   │   ├── note_path.py       # NotePath value object
│   │   │   └── time_range_filter.py # TimeRangeFilter value object
│   │   └── repositories/
│   │       └── note_repository.py  # Repository interfaces
│   └── device_management/
│       ├── entities/
│       │   └── device.py          # Device aggregate root
│       ├── value_objects/
│       │   └── device_connection.py # Connection value objects
│       └── repositories/
│           └── device_repository.py # Repository interfaces
```

### ✅ Phase 2: Application Layer

Implemented use cases and DTOs:

```
application/
├── use_cases/
│   └── find_device.py    # FindDevice use case (completed)
└── dtos/
    └── device_dto.py     # Request/Response DTOs
```

### ✅ Phase 3: Infrastructure Layer

Created infrastructure implementations:

```
infrastructure/
├── repositories/
│   └── memory_device_repository.py  # In-memory repository
└── network/
    └── network_discovery_service.py # Network scanning service
```

### ✅ Phase 4: Presentation Layer

Refactored CLI with clean separation:

```
presentation/
└── cli/
    ├── commands/
    │   └── find_command.py      # Thin command handler
    ├── container.py              # Dependency injection
    └── main_refactored.py       # New entry point
```

## Key Improvements

### 1. **Clear Domain Model**
- **Note Aggregate**: Encapsulates note lifecycle, sync status, and conversion state
- **Device Aggregate**: Manages device connections and capabilities
- **Value Objects**: Enforce business rules (e.g., valid IP addresses, note paths)

### 2. **Separated Concerns**
- **Domain Layer**: Pure business logic, no infrastructure dependencies
- **Application Layer**: Use cases orchestrate domain logic
- **Infrastructure Layer**: Adapters for external systems
- **Presentation Layer**: Thin controllers for user interaction

### 3. **Testability**
- Domain logic can be tested without infrastructure
- Use cases can be tested with mocked repositories
- Clear boundaries enable focused testing

### 4. **Domain Events**
- `NoteCreated`, `NoteSynced`, `NoteConvertedToPDF`
- `DeviceDiscovered`, `DeviceConnected`, `DeviceDisconnected`
- Enable event-driven architecture and audit trails

## Example: Find Command Refactoring

### Before (Monolithic):
```python
# cli.py - mixed concerns
if args.command == "find":
    ip = find_device()  # Direct infrastructure call
    if ip and args.open:
        url = f"http://{ip}:{args.port}"
        print(f"🌐 Opening {url} in browser...")
        webbrowser.open(url)  # UI concern in business logic
    return
```

### After (DDD):
```python
# Presentation Layer - Thin Controller
class FindCommand:
    def execute(self, args):
        request = FindDeviceRequest(open_in_browser=args.open)
        response = self._use_case.execute(request)
        self._format_output(response)

# Application Layer - Use Case
class FindDeviceUseCase:
    def execute(self, request):
        device = self._discover_or_find_device()
        if device:
            self._handle_browser_opening(device, request)
            return FindDeviceResponse.success(device)
        return FindDeviceResponse.not_found()

# Domain Layer - Pure Business Logic
class Device:
    def connect(self):
        if not self._status.is_online:
            self._status = DeviceStatus(is_online=True)
            self._raise_event(DeviceConnected(self.id))
```

## Migration Strategy

### Completed ✅
1. Domain layer structure and base classes
2. Core value objects and aggregates
3. Repository interfaces
4. Find command as proof of concept

### Next Steps 📋

#### Phase 1: Core Commands (Week 1) ✅ PARTIALLY COMPLETED
- [ ] Extract `ListFilesUseCase`
- [x] Extract `BrowseDeviceUseCase` ✅
- [x] Extract `GetDeviceInfoUseCase` ✅
- [ ] Create `NoteListingService` domain service

#### Phase 2: Download & Sync (Week 2)
- [ ] Extract `DownloadNotesUseCase`
- [ ] Implement `SynchronizationService`
- [ ] Create `FileSystemNoteRepository`
- [ ] Implement `HttpDeviceRepository`

#### Phase 3: Conversion & OCR (Week 3)
- [ ] Extract `ConvertNotesUseCase`
- [ ] Extract `ProcessOCRUseCase`
- [ ] Create adapter for `supernotelib`
- [ ] Create adapter for PDF processors

#### Phase 4: Complete Migration (Week 4)
- [ ] Replace old CLI with refactored version
- [ ] Add comprehensive tests
- [ ] Update documentation
- [ ] Remove legacy code

## Testing Strategy

### Unit Tests (Domain Layer)
```python
def test_note_needs_sync():
    note = Note.create_from_remote(...)
    assert note.needs_sync() == True
    
    note.mark_as_synced("checksum123")
    assert note.needs_sync() == False
```

### Integration Tests (Use Cases)
```python
def test_find_device_use_case():
    mock_repo = Mock(DeviceRepository)
    mock_discovery = Mock(DeviceDiscoveryService)
    
    use_case = FindDeviceUseCase(mock_repo, mock_discovery)
    response = use_case.execute(FindDeviceRequest())
    
    assert response.found == True
```

### End-to-End Tests
```python
def test_find_command_e2e():
    result = subprocess.run(['supynote', 'find'], capture_output=True)
    assert "Found Supernote device" in result.stdout
```

## Benefits Achieved

1. **Maintainability**: Clear separation of concerns makes changes easier
2. **Testability**: Each layer can be tested independently
3. **Extensibility**: New features can be added without touching existing code
4. **Domain Focus**: Business logic is explicit and centralized
5. **Flexibility**: Infrastructure can be swapped without affecting domain

## Running the Refactored Code

Test the refactored find command:
```bash
python -m supynote.presentation.cli.main_refactored find
python -m supynote.presentation.cli.main_refactored find --open
```

The refactored code coexists with the original, allowing gradual migration.