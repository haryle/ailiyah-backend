from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from litestar import Controller, delete, get, post, put
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body

from src.model.prompt import Prompt
from src.router.base import create_item, read_item_by_id, read_items_by_attrs
from src.service.storage.base import StorageServer

__all__ = (
    "PromptController",
    "create_prompt",
    "delete_prompt",
    "update_prompt",
)


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class _PromptRawDTO:
    text: str
    image: UploadFile
    request_id: UUID | None = None
    id: UUID | None = None


PromptRawDTO = Annotated[_PromptRawDTO, Body(media_type=RequestEncodingType.MULTI_PART)]


async def create_prompt(data: PromptRawDTO, session: "AsyncSession", storage: StorageServer) -> Prompt:
    image = await data.image.read()
    if image:
        image_id = await storage.create(image)
        prompt_data = Prompt(text=data.text, image=image_id, request_id=data.request_id)
    else:
        prompt_data = Prompt(text=data.text, request_id=data.request_id)
    await create_item(session, Prompt, prompt_data)
    return prompt_data


async def update_prompt(data: PromptRawDTO, session: "AsyncSession", id: UUID, storage: StorageServer) -> Prompt:
    prompt: Prompt = await read_item_by_id(session, Prompt, id)
    image = await data.image.read()
    if image:
        if prompt.image is not None:
            await storage.update(image, prompt.image)
        else:
            image_id = await storage.create(image)
            prompt.image = image_id
    else:
        if prompt.image is not None:
            await storage.delete(prompt.image)
        prompt.image = None
    prompt.text = data.text
    return prompt


async def delete_prompt(id: UUID, session: "AsyncSession", storage: StorageServer) -> None:
    prompt: Prompt = await read_item_by_id(session, Prompt, id)
    if prompt.image is not None:
        await storage.delete(prompt.image)
    await session.delete(prompt)


class PromptController(Controller):
    path = "prompt"

    @get()
    async def get_prompts(self, transaction: "AsyncSession") -> Sequence[Prompt]:
        data: Sequence[Prompt] = await read_items_by_attrs(transaction, Prompt)
        return data

    @get("/{id:uuid}")
    async def get_prompt_by_id(self, transaction: "AsyncSession", id: UUID) -> Prompt:
        return await read_item_by_id(transaction, Prompt, id)  # type: ignore[no-any-return]

    @post()
    async def create_prompt(self, data: PromptRawDTO, transaction: "AsyncSession", storage: StorageServer) -> Prompt:
        return await create_prompt(data, transaction, storage)

    @put("/{id:uuid}")
    async def update_prompt(
        self, data: PromptRawDTO, transaction: "AsyncSession", id: UUID, storage: StorageServer
    ) -> Prompt:
        return await update_prompt(data, transaction, id, storage)

    @delete("/{id:uuid}")
    async def delete_prompt(self, id: UUID, transaction: "AsyncSession", storage: StorageServer) -> None:
        return await delete_prompt(id, transaction, storage)
