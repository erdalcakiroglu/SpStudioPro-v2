"""
Connection profile model for SQL Server connections
"""

import uuid
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AuthMethod(str, Enum):
    """Authentication method for SQL Server"""
    SQL_SERVER = "sql_server"       # SQL Server Authentication
    WINDOWS = "windows"             # Windows Authentication
    AZURE_AD = "azure_ad"           # Azure Active Directory


@dataclass
class ConnectionProfile:
    """
    SQL Server connection profile
    
    Contains all information needed to connect to a SQL Server instance.
    Passwords are stored separately in the credential store.
    """
    
    # Unique identifier
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Display name
    name: str = ""
    
    # Server details
    server: str = ""
    port: int = 1433
    database: str = "master"  # Default database
    
    # Authentication
    auth_method: AuthMethod = AuthMethod.SQL_SERVER
    username: str = ""
    # Note: password is NOT stored here - use credential_store
    
    # Connection options
    driver: Optional[str] = None  # Specific driver like "ODBC Driver 17 for SQL Server"
    encrypt: bool = True
    trust_server_certificate: bool = False
    connection_timeout: int = 15
    query_timeout: int = 30
    application_name: str = "SQL Perf AI"
    
    # Organization (for grouping)
    folder: str = ""  # Folder path like "Production/US"
    tags: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_connected: Optional[datetime] = None
    color: str = ""  # Hex color for visual identification
    notes: str = ""
    
    def __post_init__(self):
        if not self.name:
            self.name = self.server
    
    @property
    def display_name(self) -> str:
        """Formatted display name"""
        if self.database and self.database != "master":
            return f"{self.name} ({self.database})"
        return self.name
    
    @property
    def connection_string_base(self) -> str:
        """
        Generate base connection string (without password)
        Password should be added by the connection manager
        """
        server = self.server
        if "\\" in server:
            server_value = server if self.port == 1433 else f"{server},{self.port}"
        else:
            server_value = f"{server},{self.port}"

        parts = [
            f"DRIVER={{ODBC Driver 18 for SQL Server}}",
            f"SERVER={server_value}",
            f"DATABASE={self.database}",
            f"APP={{{self.application_name}}}",
            f"Connect Timeout={self.connection_timeout}",
        ]
        
        if self.auth_method == AuthMethod.SQL_SERVER:
            parts.append(f"UID={self.username}")
        elif self.auth_method == AuthMethod.WINDOWS:
            parts.append("Trusted_Connection=yes")
        
        if self.encrypt:
            parts.append("Encrypt=yes")
        
        if self.trust_server_certificate:
            parts.append("TrustServerCertificate=yes")
        
        return ";".join(parts)
    
    def to_dict(self) -> dict:
        """Convert to dictionary (for JSON serialization)"""
        data = asdict(self)
        data['auth_method'] = self.auth_method.value
        data['created_at'] = self.created_at.isoformat()
        data['last_connected'] = self.last_connected.isoformat() if self.last_connected else None
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConnectionProfile':
        """Create from dictionary"""
        if 'auth_method' in data:
            data['auth_method'] = AuthMethod(data['auth_method'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'last_connected' in data and data['last_connected']:
            data['last_connected'] = datetime.fromisoformat(data['last_connected'])
        return cls(**data)
    
    def copy(self) -> 'ConnectionProfile':
        """Create a copy with new ID"""
        data = self.to_dict()
        data['id'] = str(uuid.uuid4())
        data['name'] = f"{self.name} (copy)"
        data['created_at'] = datetime.now().isoformat()
        data['last_connected'] = None
        return ConnectionProfile.from_dict(data)


class ConnectionProfileValidator(BaseModel):
    """Pydantic validator for connection profile"""
    
    name: str = Field(min_length=1, max_length=100)
    server: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535, default=1433)
    database: str = Field(min_length=1, max_length=128, default="master")
    username: str = Field(default="", max_length=128)
    
    @field_validator('server')
    @classmethod
    def validate_server(cls, v: str) -> str:
        # Remove whitespace
        v = v.strip()
        # Basic validation
        if not v:
            raise ValueError("Server name is required")
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()
