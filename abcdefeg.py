import logging
import traceback
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, UploadFile
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.readers.notion import NotionPageReader
from llama_index.readers.slack import (
        SlackReader,
    )  # Import the SlackReader module.

from llama_index.readers.discord import DiscordReader
from llama_index.readers.github import GithubRepositoryReader, GithubClient



from app.core.deps.auth import ProjectAdminDep, ProjectModeratorDep
from app.core.deps.db import SessionDep
from app.core.exceptions import CustomException
from app.core.utils.file import text_to_file, upload_embeddings_s3
from app.project.brain.brain import Brain
from app.project.schemas.embeddings import IngestOut
from app.project.schemas.schema import FindModel, TextIngestModel, URLIngestModel




from llama_index.readers.google import GoogleDriveReader


from app.project.services import dbc, ingest_service
from worker.tasks import extract_ingest_file, extract_ingest_url

router = APIRouter()

brain = Brain()
logger = logging.getLogger(__name__)


@router.post("/projects/{p_uid}/embeddings/reset")
async def reset_embeddings(
    p_uid: str,
    db: SessionDep,
    user: ProjectAdminDep,
):
    try:
        project = brain.findProject(p_uid, db)

        if project.model.type != "rag":
            raise HTTPException(
                status_code=400, detail='{"error": "Only available for RAG projects."}'
            )

        project.vector.reset(brain)

        return {
            "uid": project.model.uid,
            "name": project.model.name,
        }
    except Exception as e:
        logging.error(e)
        traceback.print_tb(e.__traceback__)
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/projects/{p_uid}/embeddings/search")
async def find_embedding(
    p_uid: str,
    embedding: FindModel,
    db: SessionDep,
    user: ProjectModeratorDep,
):
    project = brain.findProject(p_uid, db)

    if project.model.type != "rag":
        raise HTTPException(status_code=400, detail='{"error": "Only available for RAG projects."}')

    output = []

    if embedding.text:
        k = embedding.k or project.model.k or 2

        if embedding.score is not None:
            threshold = embedding.score
        else:
            threshold = embedding.score or project.model.score or 0.2

        retriever = VectorIndexRetriever(
            index=project.vector.index,
            similarity_top_k=k,
        )

        query_engine = RetrieverQueryEngine.from_args(
            retriever=retriever,
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=threshold)],
            response_mode="no_text",
        )

        response = query_engine.query(embedding.text)

        for node in response.source_nodes:
            output.append(
                {"source": node.metadata["source"], "score": node.score, "id": node.node_id}
            )

    elif embedding.source:
        output = project.vector.list_source(embedding.source)

    return {"embeddings": output}


@router.get("/projects/{p_uid}/embeddings/id/{id}")
async def get_embedding(
    p_uid: str,
    id: str,
    db: SessionDep,
    user: ProjectModeratorDep,
):
    project = brain.findProject(p_uid, db)

    if project.model.type != "rag":
        raise HTTPException(status_code=400, detail='{"error": "Only available for RAG projects."}')

    chunk = project.vector.find_id(id)
    return chunk


def handle_ingest_file_upload(session, file: UploadFile, project, user, extra_data):
    uploaded_file = upload_embeddings_s3(session, user.id, file, str(project.uid))

    ingest = ingest_service.create(
        session, user.id, project.id, uploaded_file.id, extra_data=extra_data
    )

    extract_ingest_file.delay(ingest.id)

    response = {
        "id": ingest.id,
        "chunks": ingest.number_of_page,
        "message": "We are processing your file",
    }
    return response


@router.post("/projects/{p_uid}/embeddings/ingest/text")
async def ingest_text(
    p_uid: str,
    data: TextIngestModel,
    db: SessionDep,
    user: ProjectModeratorDep,
):
    project = dbc.get_project_by_uid(db, p_uid)

    file = text_to_file(data.text)
    extra_data = {"options": "{}", "chunks": data.chunks, "splitter": data.splitter}

    return handle_ingest_file_upload(db, file, project, user, extra_data)


@router.post("/projects/{p_uid}/embeddings/ingest/text2")
async def ingest_text2(
    p_uid: str,
    gdfolder_id: str,
    db: SessionDep,
    user: ProjectModeratorDep,
):
    print("data:",gdfolder_id)
    loader = GoogleDriveReader(service_account_key_path="/Users/sabu/Documents/projects/neuwark-backend-stage/credentials.json")
    def load_data(folder_id: str):
        docs = loader.load_data(folder_id=folder_id)
        for doc in docs:
            doc.id_ = doc.metadata["file_name"]
        return docs


    docs = load_data(folder_id=gdfolder_id)
    print("docs: ",docs)
    project = brain.findProject(p_uid,db,docs)

    
    #project.vector.save()
    
    # metadata = {"source": ingest.source}
    # documents = [Document(text=ingest.text, metadata=metadata)]

    # if ingest.keywords and len(ingest.keywords) > 0:
    #     for document in documents:
    #         document.metadata["keywords"] = ", ".join(ingest.keywords)
    # else:
    #     documents = ExtractKeywordsForMetadata(documents)

    #     # for document in documents:
    #     #    document.text = document.text.decode('utf-8')

    # nchunks = IndexDocuments(project, documents, ingest.splitter, ingest.chunks)
    # project.vector.save()
# print(docs)

    # file = text_to_file(data.text)
    # extra_data = {"options": "{}", "chunks": data.chunks, "splitter": data.splitter}

    return gdfolder_id
@router.post("/projects/{p_uid}/embeddings/ingest/notion")
async def ingest_text2(
    p_uid: str,
    notion_token: str,
    db: SessionDep,
    user: ProjectModeratorDep,
):
    print("data:",notion_token)
    page_ids = ["fbc1e05d7c3a464eabe4287b07282eed"]
    reader = NotionPageReader(integration_token="secret_lyY4t65cIpOpVsyp3UQvkQajCrX47uxMhIjtZ8tjPPC")

    documents = reader.load_data(
    page_ids=["ca57b51eb3d24d8bb1864e2890737362"]
)
    # loader = GoogleDriveReader(service_account_key_path="/Users/sabu/Documents/projects/neuwark-backend-stage/credentials.json")
    def load_data(docs):
        for doc in docs:
            doc.id_ = doc.metadata["page_id"]
        return docs


    docs = load_data(documents)
    print("docs: ",docs)
    project = brain.findProject(p_uid,db,docs)
# https://github.com/run-llama/llama_index/issues/3777
    
    #project.vector.save()
    
    # metadata = {"source": ingest.source}
    # documents = [Document(text=ingest.text, metadata=metadata)]

    # if ingest.keywords and len(ingest.keywords) > 0:
    #     for document in documents:
    #         document.metadata["keywords"] = ", ".join(ingest.keywords)
    # else:
    #     documents = ExtractKeywordsForMetadata(documents)

    #     # for document in documents:
    #     #    document.text = document.text.decode('utf-8')

    # nchunks = IndexDocuments(project, documents, ingest.splitter, ingest.chunks)
    # project.vector.save()
# print(docs)

    # file = text_to_file(data.text)
    # extra_data = {"options": "{}", "chunks": data.chunks, "splitter": data.splitter}

    return notion_token
@router.post("/projects/{p_uid}/embeddings/ingest/discord")
async def ingest_text2(
    p_uid: str,
    discord_token: str,
    db: SessionDep,
    user: ProjectModeratorDep,
):
    print("data:",discord_token)
    
    channel_ids = [1252606127192018975]  # Replace with your channel_id
    reader = DiscordReader(discord_token=discord_token)
    documents = reader.load_data(channel_ids=channel_ids)
    
    # loader = GoogleDriveReader(service_account_key_path="/Users/sabu/Documents/projects/neuwark-backend-stage/credentials.json")
    def load_data(docs):
        for doc in docs:
            doc.id_ = doc.metadata["page_id"]
        return docs


    docs = load_data(documents)
    print("docs: ",docs)
    project = brain.findProject(p_uid,db,docs)
# https://github.com/run-llama/llama_index/issues/3777
    
    #project.vector.save()
    
    # metadata = {"source": ingest.source}
    # documents = [Document(text=ingest.text, metadata=metadata)]

    # if ingest.keywords and len(ingest.keywords) > 0:
    #     for document in documents:
    #         document.metadata["keywords"] = ", ".join(ingest.keywords)
    # else:
    #     documents = ExtractKeywordsForMetadata(documents)

    #     # for document in documents:
    #     #    document.text = document.text.decode('utf-8')

    # nchunks = IndexDocuments(project, documents, ingest.splitter, ingest.chunks)
    # project.vector.save()
# print(docs)

    # file = text_to_file(data.text)
    # extra_data = {"options": "{}", "chunks": data.chunks, "splitter": data.splitter}

    return discord_token
@router.post("/projects/{p_uid}/embeddings/ingest/github")
def ingest_text4(
    p_uid: str,
    github_token: str,
    db: SessionDep,
    user: ProjectModeratorDep,
):
    print("data:",github_token)
    
    
    owner = "mhsabu"
    repo = "Neugrove"
    branch = "main"

    github_client = GithubClient(github_token=github_token, verbose=False)

    reader = GithubRepositoryReader(
        github_client=github_client,
        owner=owner,
        repo=repo,
        use_parser=False,
        verbose=True,
        filter_directories=(
            ["docs"],
            GithubRepositoryReader.FilterType.INCLUDE,
        ),
        filter_file_extensions=(
            [
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".ico",
                "json",
                ".ipynb",
            ],
            GithubRepositoryReader.FilterType.EXCLUDE,
        ),
    )
    documents = reader.load_data(branch="main")

    # loader = GoogleDriveReader(service_account_key_path="/Users/sabu/Documents/projects/neuwark-backend-stage/credentials.json")
    def load_data(docs):
        for doc in docs:
            doc.id_ = doc.metadata["file_path"]
        return docs


    docs = load_data(documents)
    print("docs: ",docs)
    project = brain.findProject(p_uid,db,docs)
# https://github.com/run-llama/llama_index/issues/3777
    
    #project.vector.save()
    
    # metadata = {"source": ingest.source}
    # documents = [Document(text=ingest.text, metadata=metadata)]

    # if ingest.keywords and len(ingest.keywords) > 0:
    #     for document in documents:
    #         document.metadata["keywords"] = ", ".join(ingest.keywords)
    # else:
    #     documents = ExtractKeywordsForMetadata(documents)

    #     # for document in documents:
    #     #    document.text = document.text.decode('utf-8')

    # nchunks = IndexDocuments(project, documents, ingest.splitter, ingest.chunks)
    # project.vector.save()
# print(docs)

    # file = text_to_file(data.text)
    # extra_data = {"options": "{}", "chunks": data.chunks, "splitter": data.splitter}

    return github_token
@router.post("/projects/{p_uid}/embeddings/ingest/slack")
async def ingest_text2(
    p_uid: str,
    notion_token: str,
    db: SessionDep,
    user: ProjectModeratorDep,
):
    
    # Initialize SlackReader with specified parameters.
    documents = SlackReader(slack_token="xoxb-7291950124147-7314882042448-KMSk7JKxpdoSC1DAXbl5RcEB").load_data(
    channel_ids=["C078H51CQJZ"]
)
    # https://github.com/slackapi/bolt-python/issues/673
#     reader = SlackReader(
#         slack_token="xoxb-7291950124147-7314882042448-KMSk7JKxpdoSC1DAXbl5RcEB" # Provide the Slack API token for authentication.
#         # earliest_date=" ",  # Specify the earliest date to read conversations from.
#         # latest_date=" ",  # Specify the latest date to read conversations until.
#     )

#     # Load data from Slack channels using the initialized SlackReader.
#     documents = reader.load_data(
#         channel_ids=["C078H51CQJZ"]
#     )  # Specify the channel IDs to load data from.
    # loader = GoogleDriveReader(service_account_key_path="/Users/sabu/Documents/projects/neuwark-backend-stage/credentials.json")
    def load_data(docs):
        for doc in docs:
            doc.id_ = doc.metadata["channel"]
        return docs


    docs = load_data(documents)
    print("docs: ",docs)
    project = brain.findProject(p_uid,db,docs)
# https://github.com/run-llama/llama_index/issues/3777
    
    #project.vector.save()
    
    # metadata = {"source": ingest.source}
    # documents = [Document(text=ingest.text, metadata=metadata)]

    # if ingest.keywords and len(ingest.keywords) > 0:
    #     for document in documents:
    #         document.metadata["keywords"] = ", ".join(ingest.keywords)
    # else:
    #     documents = ExtractKeywordsForMetadata(documents)

    #     # for document in documents:
    #     #    document.text = document.text.decode('utf-8')

    # nchunks = IndexDocuments(project, documents, ingest.splitter, ingest.chunks)
    # project.vector.save()
# print(docs)

    # file = text_to_file(data.text)
    # extra_data = {"options": "{}", "chunks": data.chunks, "splitter": data.splitter}

    return notion_token
@router.post("/projects/{p_uid}/embeddings/ingest/upload")
async def ingest_file(
    p_uid: str,
    db: SessionDep,
    file: UploadFile,
    user: ProjectModeratorDep,
    options: str = Form("{}"),
    chunks: int = Form(256),
    splitter: str = Form("sentence"),
):
    project = dbc.get_project_by_uid(db, p_uid)

    extra_data = {"options": options, "chunks": chunks, "splitter": splitter}

    return handle_ingest_file_upload(db, file, project, user, extra_data)




@router.post("/projects/{p_uid}/embeddings/ingest/url")
async def ingest_url(
    p_uid: str,
    data: URLIngestModel,
    db: SessionDep,
    user: ProjectModeratorDep,
):
    project = dbc.get_project_by_uid(db, p_uid)

    extra_data = {"chunks": data.chunks, "splitter": data.splitter}

    ingest = ingest_service.create(db, user.id, project.id, url=data.url, extra_data=extra_data)

    extract_ingest_url.delay(ingest.id)

    response = {
        "id": ingest.id,
        "message": "We are processing your file",
    }

    return response


@router.get("/test_ingest/{ingest_id}")
async def test_ingest(ingest_id: int):
    message = ingest_service.process_ingest_file(ingest_id)

    return {"message": message}


@router.get("/projects/{p_uid}/embeddings/ingest/{ingest_id}/status")
async def get_ingest_status(p_uid: str, ingest_id: int, db: SessionDep, user: ProjectModeratorDep):
    project = dbc.get_project_by_uid(db, p_uid)

    status = ingest_service.get_status_of_ingest(db, project.id, ingest_id=ingest_id)

    return {"status": status}


@router.get("/projects/{p_uid}/embeddings")
async def get_embeddings(
    p_uid: str,
    session: SessionDep,
    user: ProjectModeratorDep,
    limit: int = 10,
    after: Optional[int] = None,
    q: Optional[str] = None,
):
    project = brain.findProject(p_uid, session)

    ingest_queryset = ingest_service.get_ingest_list(
        session,
        project_id=project.model.id,
        limit=limit,
        after_id=after,
        search_query=q,
    )

    after = None
    results = []
    for ingest in ingest_queryset:
        after = ingest.id
        results.append(IngestOut.model_validate(ingest))

    return {"after": after, "results": results}


@router.get("/projects/{p_uid}/embeddings/{ingest_id}")
async def get_embedding_source(
    p_uid: str,
    ingest_id: int,
    session: SessionDep,
    user: ProjectModeratorDep,
):
    project = brain.findProject(p_uid, session)

    ingest = ingest_service.get_ingest_details(session, ingest_id)

    file_path = ingest.file.file_path
    ingest_source = file_path.split("/")[-1]

    docs = project.vector.find_source(ingest_source)

    if len(docs["ids"]) == 0:
        return {"ids": []}
    else:
        return docs


@router.delete("/projects/{p_uid}/embeddings/{ingest_id}")
async def delete_embedding(
    p_uid: str,
    ingest_id: int,
    session: SessionDep,
    user: ProjectModeratorDep,
):
    project = brain.findProject(p_uid, session)

    ingest = ingest_service.get_ingest_details(session, ingest_id)
    if ingest.project_id != project.db_model.id:
        raise CustomException(message="Ingest not found")

    file_path = ingest.file.file_path
    ingest_source = file_path.split("/")[-1]

    try:
        _ = project.vector.delete_source(ingest_source)
        session.delete(ingest)
        session.commit()
    except Exception:
        raise CustomException(message="Something wrong to delete the ingest")

    return {"message": "Ingest deleted successfully"}
