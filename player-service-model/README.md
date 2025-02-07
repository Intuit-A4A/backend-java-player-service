# Player Service Model

This is a thin model wrapper container based on `Player.csv` data.

To build and run using docker:
```shell
docker build -t a4a_model .
docker run -d -p 8657:8657 a4a_model
```
OR, alternatively, using podman:
```shell
podman build -t a4a_model .
podman run --rm -p 8657:8657  -it localhost/a4a_model:latest
```


This will expose the model on port 8657.

To send an inference request to the AI model using player names:
```shell
$ curl -H "Content-type: application/json" -d '{"seed_id":"abbotji01","team_size":10}' http://127.0.0.1:8657/team/generate
{"seed_id":"abbotji01","prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a","team_size":10,"member_ids":["abbotji01","combspa01","maurero01","cummijo01","flemida01","macdobo01","eddych01","morriha02","mcgrifr01","blossgr01"]}
```

To send an inference request to the AI model using features:
```shell
To send an inference request to the AI model using a set of features:
 ```shell
$ curl -H "Content-type: application/json" -d '{"features":{"birth_year":1970, "height":70, "weight":120, "bats":"R", "throws":"L"},"team_size":10}' http://127.0.0.1:8657/team/generate
{"seed_id":null,"prediction_id":"ddedf511-2e68-4ab5-87c5-c77b8d15eb23","team_size":10,"member_ids":["roblevi01","deverra01","goharlu01","albieoz01","barrefr02","urenari01","uriasju01","verdual01","mejiafr01","sierrma01"]}
```

To send feedback about the recommendation of a prior seed:
```shell
$ curl -H "Content-type: application/json"  -d '{"seed_id":"abbotji01","member_id":"maurero01","feedback":-1,"prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a"}' http://127.0.0.1:8657/team/feedback 
{"seed_id":"abbotji01","member_id":"maurero01","accepted":true,"prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a"}
```