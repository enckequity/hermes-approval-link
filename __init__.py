"""Hermes directory-plugin entry point: registers the photon-cards approval transport."""


def register(ctx):
    from .hermes_photon_approvals.config import Settings
    from .hermes_photon_approvals.photon import PhotonSender
    from .hermes_photon_approvals.transport import present

    def approval(request):
        settings = Settings.from_env()
        return present(request, settings, PhotonSender.from_env(settings.dm))

    ctx.register_approval_transport('photon-cards', approval)
