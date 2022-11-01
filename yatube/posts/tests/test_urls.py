from http import HTTPStatus
from django.test import Client, TestCase
from ..models import Group, Post, User


class PostsURLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='noname')
        cls.other_user = User.objects.create_user(username='other_noname')
        cls.group = Group.objects.create(
            title='Test group',
            slug='test-slug',
            description='Test description'

        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='Test post text',
            group=cls.group
        )

        cls.url_edit_post = f'/posts/{str(cls.post.pk)}/edit/'
        cls.url_redirect = f'/posts/{cls.post.pk}/'
        cls.url_404 = '/page404/'
        cls.template_for_all = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user.username}/': 'posts/profile.html',
            f'/posts/{cls.post.pk}/': 'posts/post_detail.html',
        }

        cls.template_for_auth = {
            cls.url_edit_post: 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsURLTests.user)
        self.authorized_other_client = Client()
        self.authorized_other_client.force_login(PostsURLTests.other_user)

    def test_correct_templates(self):
        """Проверка использования корректного шаблона."""
        for url, template in self.template_for_all.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_redirect(self):
        """Проверка использования redirect для соответствующих страниц."""
        for url, template in self.template_for_auth.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertRedirects(response, f'/auth/login/?next={url}')

    def test_page_404(self):
        """Проверка несуществующей страницы."""
        response = self.guest_client.get(self.url_404)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_authorized_client(self):
        """Проверка доступности страниц для
           авторизованного пользователя."""
        post_id = self.post.pk
        for_auth = {
            '/create/': 'posts/create_post.html',
            f'/posts/{post_id}/edit/': 'posts/create_post.html',
        }
        for url, template in for_auth.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)
