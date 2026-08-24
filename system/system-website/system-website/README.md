# WordPress Implementation Workspace

This directory contains local WordPress implementation material for the public
website capability. The capability contract and current implementation status
are documented in the stack-level [`README.md`](../README.md).

The active root `compose.yml` currently runs the official WordPress image with
named volumes. Files in this directory are not yet built into or mounted by the
active composition, so themes, plugins, configuration, and content placed here
must not be described as reproducible product behavior until that integration
is implemented and verified.

Do not store real credentials, uploads, generated caches, or environment state
in source control.
