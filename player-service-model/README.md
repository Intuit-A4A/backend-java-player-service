# Player Service Model

This is a thin model wrapper container based on `Player.csv` data.

To build and run:
```shell
docker build -t a4a_model .
docker run -d -p 5000:5000 a4a_model
```

This will expose port 5000.

To send data to the trained AI model:
```shell
$ curl -H "Content-type: application/json" -d '{"seed_id":"abbotji01","team_size":10}' http://127.0.0.1:5000/team/generate
{"seed_id":"abbotji01","prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a","team_size":10,"member_ids":["abbotji01","combspa01","maurero01","cummijo01","flemida01","macdobo01","eddych01","morriha02","mcgrifr01","blossgr01"]}
```

To send feedback:
```shell
$ curl -H "Content-type: application/json"  -d '{"seed_id":"abbotji01","member_id":"maurero01","feedback":-1,"prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a"}' http://127.0.0.1:5000/team/feedback 
{"seed_id":"abbotji01","member_id":"maurero01","accepted":true,"prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a"}
```
