from aws_cdk import (
    assertions,
    App
)

from zen_safe.safe_stack import ZenSafeStack


# example test
def test_zen_safe_stack():
    app = App()
    stack = ZenSafeStack(app, "zen-safe", "production", "safe.zenchain.io")
    template = assertions.Template.from_stack(stack)
    pass
