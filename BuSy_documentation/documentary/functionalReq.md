# Functional requirements

> What the system does

## System's native

### Manage self static files
### User registration
### User configuration
### Server father (center)
### Server child (node)
### Authentication
> All operations must be protected with authentication mandatory. Endpoints protected with *jason web token* (jwt) verification.

**Includes:**
- Password encription.
- JWT generation.
- SQLite database usage.
- */login* page specificaly for it.
- Protected endpoints

**Files:**
- routers/authentication.py
- databases/singleton.py
- databases/schema.ipynb
- .busy/db/main.sqlite3

### System configuration
- Server node (But only one server is active)
- Client mode (Server is active, but depends from other central node)


## Customs
### Print files
- To allow access to printing utilities from LAN

### Inventory care
### Synchronization across cloud (wordpress)
- From local to cloud (genesysmi.com)
### Synchronization across nodes

### Scheduler checker (employees)

## Point of sale
### Sales
### Customer credit
### Points/Cupons
### Inventory transfer across nodes
### Search products

### Register/Edit/Delet products

**Includes:**
- Mobile commodities.

### Vendor comissions 
### Sales cancel
### Print tickets
### Payment methods
- Allow multiple payment methods
    - Cash
    - Debit/Credit card
    - Back transfer.
    - Credit
