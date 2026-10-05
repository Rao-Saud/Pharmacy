Field-Level Validation 
DRF looks for a method matching the pattern validate_<field_name>. Because it found a valid user object, it automatically calls validate_pharmacist(self, value), passing that resolved CustomUser object into the value parameter.
Let's break down the logic inside your method line-by-line:

if value and getattr(value, 'role', None) != RoleChoices.PHARMACIST:

• value: This ensures that an object actually exists and wasn't sent as None or null (if the field allowed it).
• getattr(value, 'role', None): This safely looks for the .role attribute on the user object. If for some reason the user object doesn't have a role field, it safely defaults to None instead of crashing your application with an AttributeError.
• != RoleChoices.PHARMACIST: It evaluates the user's role against your project's strict Enum/Choice rule.
