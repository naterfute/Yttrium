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



## Migration Guide

> [!IMPORTANT]
> We Have MIGRATIONS!!!!!!
> Using A very cool library called [alembic](https://pypi.org/project/alembic/)
> We now will use alembic to securely store our database migrations to prevent any
> "Mishaps" From happening in the future

To use the migrations, you don't have to do anything. The program will deal with them
by it's self!


## Future Plans

- [ ] More advanced metadata manager
- [ ] Web GUI for making requests
- [ ] PWA for mobile app support

- [ ] Basically Lidarr but for youtube only?
