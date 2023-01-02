
# Running Calliope

Calliope can be run locally from the command line, in a local Docker container, or in Google Cloud.

To start a local Calliope server:
```
uvicorn app:app --reload
```

# Clio
Clio is a Calliope client that can be run in a Web browser, located at <calliope-host>/clio/

It will ask to use your Web cam. If you let it, it will use still images from the camera to help feed the
Calliope story strategies. It shows images and text from the story.

