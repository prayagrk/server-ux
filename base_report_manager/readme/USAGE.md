Once report access is configured for a Role:

1. Assign the Role to a user (and ensure the Role is active).
2. The user navigates to the target model (e.g., Sales Orders).
3. Under the **Print** action menu, the user will only see the specific reports that have been explicitly allowed by their active Roles. All other reports are hidden.

**Note on New Reports:** Under the "Deny by Default" model, installing new modules that add reports will hide those reports from all users (except superusers) until they are explicitly added to the allowed reports of the appropriate Role's implied groups.
