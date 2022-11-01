import shutil
import tempfile


from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, User, Comment, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

SLICE_POSTS = 10
ALL_POSTS = 13


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TestImagePages(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create(username='noname')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group_test = Group.objects.create(
            title='Test group',
            slug='slug',
            description='Test description'
        )
        cls.post = Post.objects.create(
            text='Text',
            group=cls.group_test,
            author=cls.user,
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_context_image(self):
        """Изображение передается: на главную страницу сайта,
           на страницу выбранной группы,
           в профайл пользователя, на отдельную страницу поста.
        """
        template = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group_test.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for page in template:
            response = self.authorized_client.get(page)
            first_object = response.context['page_obj'][0]
            self.assertEqual(first_object.image, self.post.image)
        page = reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        response = self.authorized_client.get(page)
        self.assertEqual(response.context.get('post').image, self.post.image)


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='noname')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Test group',
            slug='slug',
            description='Test description'
        )

        cls.post = [
            Post.objects.create(
                text='Text',
                group=cls.group,
                author=cls.user
            )
            for i in range(ALL_POSTS)]

    def test_first_page(self):
        """Тестирование первой страницы paginator"""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), SLICE_POSTS)

    def test_second_page(self):
        """Тестирование второй страницы paginator"""
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']), ALL_POSTS - SLICE_POSTS
        )


class PostViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='noname',
            first_name='first_name',
            last_name='last_name'
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Test group',
            slug='slug',
            description='Test description'
        )
        cls.other_group = Group.objects.create(
            title='Test other group',
            slug='other-slug',
            description='Test other description'
        )
        cls.post = Post.objects.create(
            text='Text',
            group=cls.group,
            author=cls.user,
        )

    def test_pages_correct_templates(self):
        """Проверка использования корректного шаблона."""
        template = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.pk}
            ): 'posts/create_post.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }
        for reverse_name, template in template.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_context_index_group_list_profile(self):
        """Пост появляется: на главной странице сайта, на странице выбранной группы,
           в профайле пользователя.
        """
        template = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        ]
        for page in template:
            response = self.authorized_client.get(page)
            first_object = response.context['page_obj'][0]
            self.assertEqual(first_object.text, self.post.text)
            self.assertEqual(
                first_object.author.get_full_name(), self.user.get_full_name())
            self.assertEqual(first_object.group.slug, self.group.slug)

    def test_post_detail(self):
        """Проверка страницы post_detail."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.assertEqual(
            response.context.get('post').text, self.post.text)
        self.assertEqual(
            response.context.get('post').author.get_full_name(),
            self.user.get_full_name()
        )
        self.assertEqual(
            response.context.get('post').group.slug, self.group.slug
        )

    def test_context_posts_create(self):
        """Проверка страницы post_create."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for tag, expected in form_fields.items():
            with self.subTest(tag=tag):
                form_field = response.context.get('form').fields.get(tag)
                self.assertIsInstance(form_field, expected)

    def test_context_post_edit(self):
        """Проверка страницы post_edit."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for tag, expected in form_fields.items():
            with self.subTest(tag=tag):
                form_field = response.context.get('form').fields.get(tag)
                self.assertIsInstance(form_field, expected)

    def test_post_in_group(self):
        """Проверка попал ли пост в группу, для которой не был предназначен."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': self.other_group.slug})
        )
        count_object = len(response.context['page_obj'])
        self.assertEqual(count_object, 0)

    def test_cache_index(self):
        """Проверка работы кеша страницы index."""
        response = self.authorized_client.get(reverse('posts:index'))
        Post.objects.create(
            text='Text',
            group=self.group,
            author=self.user,
        )
        response2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response2.content)
        cache.clear()
        response3 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(
            len(response3.context['page_obj']),
            len(response.context['page_obj']) + 1
        )


class ComentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='noname')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Test group',
            slug='slug',
            description='Test description'
        )
        cls.post = Post.objects.create(
            text='Text',
            group=cls.group,
            author=cls.user
        )
        cls.comment_test = Comment.objects.create(
            text='Text comment',
            post=cls.post,
            author=cls.user
        )

    def test_comment_add(self):
        """Проверка того, что после успешной отправки
            комментарий появляется на странице поста.
        """
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}),
        )
        obj = response.context['comments'][0]
        self.assertEqual(obj.text, self.comment_test.text)
        self.assertEqual(obj.author, self.comment_test.author)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='noname')
        cls.user2 = User.objects.create(username='noname2')
        cls.user3 = User.objects.create(username='noname3')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.authorized_client2 = Client()
        cls.authorized_client2.force_login(cls.user2)
        cls.group = Group.objects.create(
            title='Test group',
            slug='slug',
            description='Test description'
        )
        cls.post = Post.objects.create(
            text='Text',
            group=cls.group,
            author=cls.user
        )
        cls.test_follow = Follow.objects.create(
            user=cls.user,
            author=cls.user2
        )

    def test_profile_follow(self):
        """Проверка того, что авторизованный пользователь
            может подписываться на других пользователей.
        """
        follow = Follow.objects.count()
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user3.username}
        ))
        self.assertEqual(Follow.objects.count(), follow + 1)
        other_follow = Follow.objects.last()
        self.assertEqual(other_follow.user, self.user)
        self.assertEqual(other_follow.author, self.user3)

    def test_profile_unfollow(self):
        """Проверка того, что авторизованный пользователь
            может удалять из подписок других пользователей.
        """
        follow = Follow.objects.count()
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user2.username}
        ))
        self.assertEqual(Follow.objects.count(), follow - 1)

    def test_add_post_in_follower(self):
        """Проверка того, что новая запись пользователя
           появляется в ленте тех, кто на него подписан.
        """
        Follow.objects.create(
            user=self.user,
            author=self.user3,
        )
        post = Post.objects.create(
            text='Text',
            group=self.group,
            author=self.user3,
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual((response.context['page_obj'][0]).text, post.text)

    def test_no_add_post_in_follower(self):
        """Проверка того, что новая запись пользователя
           не появляется в ленте тех, кто на него не подписан.
        """
        posts = Post.objects.filter(author=self.user2).count()
        Post.objects.create(
            text='Text',
            group=self.group,
            author=self.user3,
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), posts)
