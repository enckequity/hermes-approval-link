"""Hermes directory-plugin entry point: registers the approval-link transport."""


def register(ctx):
    from .approval_link.config import Settings
    from .approval_link.transport import present

    ctx.register_approval_transport('approval-link', lambda request: present(request, Settings.from_env()))
