import dataclasses
import random
import time
import uuid
from typing import Literal, Optional

import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_pydantic import validate
import joblib
from pydantic import BaseModel

nn_model = joblib.load("team_model.joblib")
player_db = pd.read_csv("features_db.csv")
all_players = set(player_db["playerID"])
features = ["birthZ", "heightZ", "weightZ", "batsN", "throwsN"]

@dataclasses.dataclass
class Stats:
    mean: float
    std: float

    def z(self, x):
        return (x - self.mean)/self.std

player_stats = {
    "height": Stats(player_db["height"].mean(), player_db["height"].std()),
    "weight": Stats(player_db["weight"].mean(), player_db["weight"].std()),
    "birthFraction": Stats(player_db["birthFraction"].mean(), player_db["birthFraction"].std()),
}

# list of feedback exclusions
exclude_db = {}

app = Flask(__name__)


class TeamException(Exception):
    pass

class Features(BaseModel):
    birth_year: Optional[float] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    bats: Optional[Literal["L", "R", "N"]] = None
    throws: Optional[Literal["L", "R", "N"]] = None

class TeamGenerateInput(BaseModel):
    # either a seed or features need to be provided
    seed_id: Optional[str] = None
    features: Optional[Features] = None
    team_size: int


class TeamGenerateOutput(BaseModel):
    seed_id: Optional[str]
    prediction_id: str
    team_size: int
    member_ids: list[str]


class TeamFeedbackInput(BaseModel):
    seed_id: str
    member_id: str
    feedback: Literal[-1, 1]   # expect -1 or 1
    prediction_id: str


class TeamFeedbackOutput(BaseModel):
    seed_id: str
    prediction_id: str
    member_id: str
    accepted: bool


@app.post('/team/generate')
@validate()
def generate_team(body: TeamGenerateInput) -> TeamGenerateOutput:
    # Implement logic to generate a team based on the provided data

    # 1% of the time, the model will fail to return a result
    failure_simulator = random.random()
    if failure_simulator < 0.01:
        raise TimeoutError("Unable to generate result.")
    elif failure_simulator < 0.02:
        time.sleep(6.0)

    seed = body.seed_id
    if body.seed_id:
        try:
            seed_features = player_db[player_db.playerID == seed][features]
        except:
            raise TeamException(f"The seed {body.seed_id} has no associated player")
    elif body.features:
        batsN = 1.0 if body.features.bats == 'R' else -1.0 if body.features.bats == 'L' else 0.0
        throwsN = 1.0 if body.features.throws == 'R' else -1.0 if body.features.throws == 'L' else 0.0
        heightZ = player_stats["height"].z(body.features.height) if body.features.height is not None else 0.0
        weightZ = player_stats["weight"].z(body.features.weight) if body.features.weight is not None else 0.0
        birthZ = player_stats["birthFraction"].z(body.features.birth_year) if body.features.birth_year is not None else 0.0
        seed_features = np.array([birthZ, heightZ, weightZ, batsN, throwsN]).reshape(1, -1)
    else:
        raise TeamException("The payload must include either seed_id or features")

    team_size = body.team_size + len(exclude_db.get(seed, []))

    member_indices = nn_model.kneighbors(seed_features, team_size, return_distance=False)
    # run exclusions
    print(f"{seed=} {seed_features=} has {exclude_db.get(seed)=}")
    member_ids = [m
                  for m in list(player_db.take(member_indices[0])["playerID"])
                  if m not in exclude_db.get(seed, set())]
    print(f"{member_ids=}")

    return TeamGenerateOutput(
        seed_id=seed,
        prediction_id=str(uuid.uuid4()),
        team_size=len(member_ids),
        member_ids=member_ids
    )


@app.route('/team/feedback', methods=['POST'])
@validate()
def team_feedback(body: TeamFeedbackInput) -> TeamFeedbackOutput:
    seed_id = body.seed_id
    member_id = body.member_id
    prediction_id = body.prediction_id
    accepted = True
    if seed_id not in all_players:
        accepted = False
    elif body.feedback < 0:
        if seed_id in exclude_db:
            exclude_db[seed_id].add(member_id)
        else:
            exclude_db[seed_id] = {member_id}
    # Implement logic to process feedback for a team
    return TeamFeedbackOutput(
        seed_id=seed_id,
        member_id=member_id,
        accepted=accepted,
        prediction_id=prediction_id or str(uuid.uuid4()),
    )


class LLMInput(BaseModel):
    system_prompt: Optional[str]
    user_prompt: str

class LLMOutput(BaseModel):
    response: str

class LLMFeedbackInput(BaseModel):
    feedback: str

class LLMFeedbackOutput(BaseModel):
    system_prompt: Optional[str]
    user_prompt: str

@app.route('/llm/generate', methods=['POST'])
@validate()
def generate_description(body: LLMInput) -> LLMOutput:
    data = request.json
    # Implement logic to generate a description based on the provided data
    description = {"description": "Generated Description"}
    return jsonify(description), 201


@app.route('/llm/feedback', methods=['POST'])
@validate()
def description_feedback(body: LLMFeedbackInput) -> LLMFeedbackOutput:
    data = request.json
    # Implement logic to process feedback for a description
    feedback = {"message": "Description feedback received"}
    return jsonify(feedback), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8657, debug=True)
