from guard import SecurityConfig, SecurityDecorator


security_config = SecurityConfig(enable_redis=False, enable_rate_limiting=True)
guard_decorator = SecurityDecorator(security_config)
