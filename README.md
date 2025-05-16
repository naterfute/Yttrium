# yt-dlf server rewrite

> [!WARNING]
> This is not production ready. Not even close
> We are missing authentication and any sort of security!
> That being said, DO NOT DEPLOY TO A PRODUCTION ENVIRONMENT!!!

## What is this branch?

This branch is going to be **another** rewrite of the server side web api,
this time though, we are swapping web frameworks, we are using a relitively new
one called [robyn](https://robyn.tech/), It's a python framework built in rust.
I have no idea how this is going to affect the app, but there is only one way
to find out.
It has occured to me that I have put un-precedented time into this branch.
I've basically abandoned the FastAPI branch, so this will become the main branch
once it's ready for production use


## Migration Guide

> [!IMPORTANT]
> Migrations are handled automatically.
> Using A very cool library called [alembic](https://pypi.org/project/alembic
> This does mean that you can go up as much as you want as many times as you want skipping as many versions as you want.
> but going down can and **WILL** make your app unusable and possibly corrupt all the data in it


## Future Plans

- [ ] More advanced metadata manager
- [ ] Web GUI for making requests
- [ ] PWA for mobile app support

- [ ] Basically Lidarr but for youtube only?
